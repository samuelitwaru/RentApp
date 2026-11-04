from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Property, Unit
from receipts.models import ReceiptShare
from tenants.models import Tenancy, Tenant

from .models import Payment

User = get_user_model()


def _make_tenancy(is_active=True, rent=300_000):
    prop = Property.objects.create(name="Test Property")
    unit = Unit.objects.create(property=prop, name="A1", monthly_rent=rent)
    tenant = Tenant.objects.create(full_name="Jane Doe", phone="+256772000111")
    return Tenancy.objects.create(
        tenant=tenant,
        unit=unit,
        start_date=date.today(),
        agreed_monthly_rent=rent,
        is_active=is_active,
    )


class PaymentAmountValidationTests(TestCase):
    def test_zero_amount_is_rejected(self):
        tenancy = _make_tenancy()
        payment = Payment(
            tenancy=tenancy,
            amount=0,
            payment_date=date.today(),
            period_start=date.today(),
            period_end=date.today(),
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()


class RecordPaymentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="landlord", password="pw12345")
        self.client.force_login(self.user)

    def _post_payment(self, tenancy, confirm_inactive=False):
        data = {
            "tenancy": tenancy.pk,
            "amount": 300_000,
            "payment_date": date.today().isoformat(),
            "period_start": date.today().replace(day=1).isoformat(),
            "period_end": date.today().replace(day=1).isoformat(),
            "method": Payment.METHOD_CASH,
            "reference": "",
            "notes": "",
        }
        if confirm_inactive:
            data["confirm_inactive"] = "on"
        return self.client.post(reverse("payment_create"), data)

    def test_active_tenancy_creates_payment_and_receipt(self):
        tenancy = _make_tenancy(is_active=True)
        response = self._post_payment(tenancy)
        payment = Payment.objects.get(tenancy=tenancy)
        self.assertRedirects(response, reverse("payment_detail", args=[payment.pk]))
        self.assertTrue(hasattr(payment, "receipt"))

    def test_inactive_tenancy_blocked_without_confirmation(self):
        tenancy = _make_tenancy(is_active=False)
        response = self._post_payment(tenancy)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.filter(tenancy=tenancy).count(), 0)
        self.assertContains(response, "inactive")

    def test_inactive_tenancy_allowed_with_confirmation(self):
        tenancy = _make_tenancy(is_active=False)
        response = self._post_payment(tenancy, confirm_inactive=True)
        payment = Payment.objects.get(tenancy=tenancy)
        self.assertRedirects(response, reverse("payment_detail", args=[payment.pk]))


class WhatsappShareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="landlord", password="pw12345")
        self.client.force_login(self.user)
        tenancy = _make_tenancy()
        self.payment = Payment.objects.create(
            tenancy=tenancy,
            amount=300_000,
            payment_date=date.today(),
            period_start=date.today().replace(day=1),
            period_end=date.today().replace(day=1),
        )

    def test_share_logs_and_redirects_to_wa_me(self):
        response = self.client.get(reverse("receipt_share_whatsapp", args=[self.payment.pk, "pdf"]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://wa.me/256772000111"))
        self.assertEqual(ReceiptShare.objects.filter(payment=self.payment).count(), 1)
        share = ReceiptShare.objects.get(payment=self.payment)
        self.assertEqual(share.format, "pdf")
        self.assertEqual(share.shared_by, self.user)
