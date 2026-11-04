from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import LandlordProfile
from core.public_views import public_view
from messaging.whatsapp import build_whatsapp_link
from payments.models import Payment
from .models import ReceiptShare
from .services import get_or_create_receipt, render_receipt_jpg, render_receipt_pdf

EXPIRY_DAYS = getattr(settings, "RECEIPT_SHARE_LINK_EXPIRY_DAYS", 30)
_signer = TimestampSigner(salt="receipts.share")


@login_required
def download_receipt_pdf(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    receipt = get_or_create_receipt(payment)
    pdf_bytes = render_receipt_pdf(payment)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{receipt.receipt_number}.pdf"'
    return response


@login_required
def download_receipt_jpg(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    receipt = get_or_create_receipt(payment)
    jpg_bytes = render_receipt_jpg(payment)
    response = HttpResponse(jpg_bytes, content_type="image/jpeg")
    response["Content-Disposition"] = f'attachment; filename="{receipt.receipt_number}.jpg"'
    return response


@login_required
def share_receipt_whatsapp(request, pk, fmt):
    payment = get_object_or_404(Payment, pk=pk)
    receipt = get_or_create_receipt(payment)

    token = _signer.sign(str(payment.pk))
    expires_at = timezone.now() + timedelta(days=EXPIRY_DAYS)
    ReceiptShare.objects.create(
        payment=payment, format=fmt, token=token, expires_at=expires_at, shared_by=request.user
    )

    link = request.build_absolute_uri(reverse("public_receipt", args=[token, fmt]))
    landlord = LandlordProfile.get_solo()
    message = landlord.whatsapp_receipt_template.format(
        tenant=payment.tenancy.tenant.full_name,
        amount=f"{int(payment.amount):,}",
        period=payment.period_display(),
        receipt_no=receipt.receipt_number,
        link=link,
    )
    return redirect(build_whatsapp_link(payment.tenancy.tenant.phone, message))


def _signed_token_to_payment(token):
    try:
        payment_pk = _signer.unsign(token, max_age=EXPIRY_DAYS * 86400)
    except (BadSignature, SignatureExpired):
        return None
    return Payment.objects.filter(pk=payment_pk).first()


@public_view(rate="30/h")
def public_receipt_view(request, token, fmt):
    payment = _signed_token_to_payment(token)
    if payment is None:
        return render(request, "receipts/link_invalid.html", status=410)

    receipt = get_or_create_receipt(payment)
    if fmt == "jpg":
        body = render_receipt_jpg(payment)
        content_type = "image/jpeg"
        ext = "jpg"
    else:
        body = render_receipt_pdf(payment)
        content_type = "application/pdf"
        ext = "pdf"

    response = HttpResponse(body, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{receipt.receipt_number}.{ext}"'
    return response
