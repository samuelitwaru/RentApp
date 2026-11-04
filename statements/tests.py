from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import LandlordProfile, Property, Unit
from payments.models import Payment
from tenants.models import Tenancy, Tenant

from .models import LinkRequest, TenantAccessLink
from .services import generate_raw_token, hash_token

User = get_user_model()


def _make_tenant(name="Jane Doe", phone="+256772000111"):
    return Tenant.objects.create(full_name=name, phone=phone)


def _make_tenancy(tenant, rent=300_000):
    prop = Property.objects.create(name=f"Property for {tenant.full_name}")
    unit = Unit.objects.create(property=prop, name="A1", monthly_rent=rent)
    return Tenancy.objects.create(
        tenant=tenant, unit=unit, start_date=date.today(), agreed_monthly_rent=rent
    )


def _make_link(tenant, expires_in=timedelta(days=7), revoked=False):
    raw = generate_raw_token()
    return raw, TenantAccessLink.objects.create(
        tenant=tenant,
        token_hash=hash_token(raw),
        expires_at=timezone.now() + expires_in,
        revoked=revoked,
    )


class AccessLinkValidityTests(TestCase):
    def test_expired_link_shows_expired_page(self):
        tenant = _make_tenant()
        raw, link = _make_link(tenant, expires_in=timedelta(days=-1))
        response = self.client.get(reverse("public_statement", args=[raw]))
        self.assertEqual(response.status_code, 410)
        self.assertContains(response, "expired", status_code=410)

    def test_revoked_link_shows_expired_page(self):
        tenant = _make_tenant()
        raw, link = _make_link(tenant, revoked=True)
        response = self.client.get(reverse("public_statement", args=[raw]))
        self.assertEqual(response.status_code, 410)

    def test_nonexistent_token_shows_same_page(self):
        response = self.client.get(reverse("public_statement", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 410)

    def test_valid_link_without_pin_requirement_shows_statement(self):
        LandlordProfile.objects.create(business_name="X", require_statement_pin=False)
        tenant = _make_tenant()
        _make_tenancy(tenant)
        raw, link = _make_link(tenant)
        response = self.client.get(reverse("public_statement", args=[raw]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, tenant.full_name)
        link.refresh_from_db()
        self.assertEqual(link.access_count, 1)
        self.assertIsNotNone(link.last_accessed_at)


class PinGateTests(TestCase):
    def setUp(self):
        LandlordProfile.objects.create(business_name="X", require_statement_pin=True)
        self.tenant = _make_tenant(phone="+256772001234")
        _make_tenancy(self.tenant)
        self.raw, self.link = _make_link(self.tenant)
        self.url = reverse("public_statement", args=[self.raw])

    def test_wrong_pin_shows_form_again(self):
        response = self.client.post(self.url, {"pin": "0000"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect PIN")

    def test_correct_pin_shows_statement(self):
        response = self.client.post(self.url, {"pin": "1234"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.full_name)

    def test_lockout_after_five_failed_attempts(self):
        for _ in range(5):
            response = self.client.post(self.url, {"pin": "0000"})
        self.assertContains(response, "Too many incorrect attempts")
        # Even the correct PIN is now rejected until the lockout expires.
        response = self.client.post(self.url, {"pin": "1234"})
        self.assertContains(response, "Too many incorrect attempts")


class TenantIsolationTests(TestCase):
    def test_link_cannot_access_other_tenants_payment(self):
        LandlordProfile.objects.create(business_name="X", require_statement_pin=False)
        tenant_a = _make_tenant("Tenant A", "+256772000001")
        tenant_b = _make_tenant("Tenant B", "+256772000002")
        tenancy_b = _make_tenancy(tenant_b)
        payment_b = Payment.objects.create(
            tenancy=tenancy_b,
            amount=300_000,
            payment_date=date.today(),
            period_start=date.today().replace(day=1),
            period_end=date.today().replace(day=1),
        )
        raw_a, _ = _make_link(tenant_a)

        response = self.client.get(
            reverse("public_statement_receipt", args=[raw_a, payment_b.pk, "pdf"])
        )
        self.assertEqual(response.status_code, 404)


class InternalStatementViewTests(TestCase):
    def test_requires_login(self):
        tenant = _make_tenant()
        response = self.client.get(reverse("tenant_statement", args=[tenant.pk]))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_view_without_access_link(self):
        LandlordProfile.objects.create(business_name="X", require_statement_pin=True)
        user = User.objects.create_user(username="landlord", password="pw12345")
        self.client.force_login(user)
        tenant = _make_tenant()
        _make_tenancy(tenant)
        response = self.client.get(reverse("tenant_statement", args=[tenant.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, tenant.full_name)


class LinkRequestDedupTests(TestCase):
    def test_repeated_requests_within_an_hour_do_not_duplicate(self):
        LandlordProfile.objects.create(
            business_name="X", whatsapp_number="+256772000000"
        )
        tenant = _make_tenant()
        _make_tenancy(tenant)
        raw, link = _make_link(tenant, expires_in=timedelta(days=-1))
        url = reverse("request_new_link", args=[raw])

        response1 = self.client.post(url)
        self.assertEqual(response1.status_code, 302)
        self.assertTrue(response1.url.startswith("https://wa.me/"))
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 302)

        self.assertEqual(LinkRequest.objects.filter(tenant=tenant).count(), 1)

    def test_request_recorded_against_expired_link(self):
        LandlordProfile.objects.create(business_name="X", whatsapp_number="+256772000000")
        tenant = _make_tenant()
        raw, link = _make_link(tenant, expires_in=timedelta(days=-1))
        self.client.post(reverse("request_new_link", args=[raw]))
        link_request = LinkRequest.objects.get(tenant=tenant)
        self.assertEqual(link_request.access_link, link)
        self.assertFalse(link_request.handled)
