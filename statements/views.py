import hmac
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.models import LandlordProfile
from core.public_views import public_view
from messaging.whatsapp import build_whatsapp_link
from tenants.models import Tenant
from tenants.services import get_tenant_statement_data
from .forms import AccessLinkCreateForm, StatementPinForm
from .models import LinkRequest, TenantAccessLink
from .services import generate_raw_token, hash_token

PIN_LOCKOUT_MINUTES = 15
PIN_MAX_ATTEMPTS = 5
DEDUP_WINDOW_MINUTES = 60


def _compute_expiry(cleaned):
    choice = cleaned["expiry_choice"]
    now = timezone.now()
    if choice == "24h":
        return now + timedelta(hours=24)
    if choice == "7d":
        return now + timedelta(days=7)
    if choice == "30d":
        return now + timedelta(days=30)
    dt = cleaned["custom_expiry"]
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


class AccessLinkCreateView(LoginRequiredMixin, View):
    def get(self, request, tenant_pk):
        tenant = get_object_or_404(Tenant, pk=tenant_pk)
        form = AccessLinkCreateForm()
        return render(
            request,
            "statements/access_link_form.html",
            {"form": form, "tenant": tenant},
        )

    def post(self, request, tenant_pk):
        tenant = get_object_or_404(Tenant, pk=tenant_pk)
        form = AccessLinkCreateForm(request.POST)
        if not form.is_valid():
            return render(
                request, "statements/access_link_form.html", {"form": form, "tenant": tenant}
            )

        expires_at = _compute_expiry(form.cleaned_data)
        if form.cleaned_data.get("revoke_others"):
            TenantAccessLink.objects.filter(tenant=tenant, revoked=False).update(revoked=True)

        raw_token = generate_raw_token()
        link = TenantAccessLink.objects.create(
            tenant=tenant,
            token_hash=hash_token(raw_token),
            created_by=request.user,
            expires_at=expires_at,
        )
        statement_url = request.build_absolute_uri(reverse("public_statement", args=[raw_token]))
        landlord = LandlordProfile.get_solo()
        message = landlord.whatsapp_statement_template.format(
            tenant=tenant.full_name,
            link=statement_url,
            expiry=link.expires_at.strftime("%d %b %Y, %I:%M %p"),
        )
        return render(
            request,
            "statements/access_link_created.html",
            {
                "tenant": tenant,
                "link": link,
                "statement_url": statement_url,
                "whatsapp_url": build_whatsapp_link(tenant.phone, message),
            },
        )


@login_required
def revoke_access_link(request, pk):
    link = get_object_or_404(TenantAccessLink, pk=pk)
    if request.method == "POST":
        link.revoked = True
        link.save(update_fields=["revoked"])
        messages.success(request, "Access link revoked.")
    return redirect("tenant_detail", pk=link.tenant.pk)


@login_required
def handle_link_request(request, pk):
    link_request = get_object_or_404(LinkRequest, pk=pk)
    if request.method == "POST":
        tenant = link_request.tenant
        raw_token = generate_raw_token()
        link = TenantAccessLink.objects.create(
            tenant=tenant,
            token_hash=hash_token(raw_token),
            created_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )
        link_request.handled = True
        link_request.handled_at = timezone.now()
        link_request.save(update_fields=["handled", "handled_at"])

        statement_url = request.build_absolute_uri(reverse("public_statement", args=[raw_token]))
        landlord = LandlordProfile.get_solo()
        message = landlord.whatsapp_statement_template.format(
            tenant=tenant.full_name,
            link=statement_url,
            expiry=link.expires_at.strftime("%d %b %Y, %I:%M %p"),
        )
        return render(
            request,
            "statements/access_link_created.html",
            {
                "tenant": tenant,
                "link": link,
                "statement_url": statement_url,
                "whatsapp_url": build_whatsapp_link(tenant.phone, message),
            },
        )
    return redirect("dashboard")


def _lookup_link(token):
    return (
        TenantAccessLink.objects.filter(token_hash=hash_token(token))
        .select_related("tenant")
        .first()
    )


def _pin_session_key(token_hash):
    return f"stmt:{token_hash}"


@public_view(rate="30/h")
def public_statement_view(request, token):
    link = _lookup_link(token)
    if link is None or not link.is_valid():
        return render(
            request, "statements/link_expired.html", {"link": link, "token": token}, status=410
        )

    landlord = LandlordProfile.get_solo()
    session_key = _pin_session_key(link.token_hash)
    session_state = request.session.get(session_key, {})

    if landlord.require_statement_pin and not session_state.get("verified"):
        locked_until = session_state.get("locked_until")
        if locked_until and timezone.now().isoformat() < locked_until:
            return render(request, "statements/locked_out.html", {"locked_until": locked_until})

        form = StatementPinForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            expected = str(link.tenant.phone)[-4:]
            if hmac.compare_digest(form.cleaned_data["pin"], expected):
                session_state = {"verified": True}
                request.session[session_key] = session_state
            else:
                attempts = session_state.get("attempts", 0) + 1
                session_state["attempts"] = attempts
                if attempts >= PIN_MAX_ATTEMPTS:
                    session_state["locked_until"] = (
                        timezone.now() + timedelta(minutes=PIN_LOCKOUT_MINUTES)
                    ).isoformat()
                    session_state["attempts"] = 0
                    request.session[session_key] = session_state
                    return render(
                        request,
                        "statements/locked_out.html",
                        {"locked_until": session_state["locked_until"]},
                    )
                request.session[session_key] = session_state
                form.add_error("pin", "Incorrect PIN.")

        if not session_state.get("verified"):
            return render(request, "statements/pin_gate.html", {"form": form, "tenant": link.tenant})

    link.last_accessed_at = timezone.now()
    link.access_count += 1
    link.save(update_fields=["last_accessed_at", "access_count"])

    tenant = link.tenant
    tenancies = get_tenant_statement_data(tenant)

    return render(
        request,
        "statements/statement.html",
        {"tenant": tenant, "tenancies": tenancies, "link": link, "token": token},
    )


class TenantStatementView(LoginRequiredMixin, View):
    """Lets logged-in staff view a tenant's statement directly, without an access link."""

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        tenancies = get_tenant_statement_data(tenant)
        return render(
            request,
            "statements/statement.html",
            {"tenant": tenant, "tenancies": tenancies, "is_internal": True},
        )


@public_view(rate="60/h")
def public_statement_receipt(request, token, payment_pk, fmt):
    from receipts.services import render_receipt_jpg, render_receipt_pdf
    from django.http import HttpResponse

    link = _lookup_link(token)
    if link is None or not link.is_valid():
        return render(
            request, "statements/link_expired.html", {"link": link, "token": token}, status=410
        )

    payment = get_object_or_404(_payment_for_tenant(link.tenant, payment_pk))

    if fmt == "jpg":
        body = render_receipt_jpg(payment)
        content_type = "image/jpeg"
    else:
        body = render_receipt_pdf(payment)
        content_type = "application/pdf"

    response = HttpResponse(body, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="receipt.{fmt}"'
    return response


def _payment_for_tenant(tenant, payment_pk):
    from payments.models import Payment

    return Payment.objects.filter(pk=payment_pk, tenancy__tenant=tenant)


@public_view(rate="10/h")
def request_new_link(request, token):
    link = _lookup_link(token)
    if link is None:
        return render(request, "statements/link_expired.html", {"link": None})

    if request.method == "POST":
        cutoff = timezone.now() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        recent = LinkRequest.objects.filter(
            tenant=link.tenant, access_link=link, requested_at__gte=cutoff
        ).exists()
        if not recent:
            LinkRequest.objects.create(tenant=link.tenant, access_link=link)

        landlord = LandlordProfile.get_solo()
        message = landlord.whatsapp_link_request_template.format(
            tenant=link.tenant.full_name, unit=_tenant_latest_unit(link.tenant)
        )
        return redirect(build_whatsapp_link(landlord.whatsapp_number, message))

    return render(request, "statements/link_expired.html", {"link": link})


def _tenant_latest_unit(tenant):
    tenancy = tenant.tenancies.first()
    return tenancy.unit if tenancy else ""
