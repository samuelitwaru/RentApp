from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Property, Unit
from payments.models import Payment
from tenants.models import Tenancy, Tenant

from .services import allocate_receipt_number, amount_in_words, get_or_create_receipt
from .views import _signer

User = get_user_model()


def _make_payment(amount=450_000, payment_date=None):
    prop = Property.objects.create(name="Test Property")
    unit = Unit.objects.create(property=prop, name="A1", monthly_rent=amount)
    tenant = Tenant.objects.create(full_name="Jane Doe", phone="+256772000111")
    tenancy = Tenancy.objects.create(
        tenant=tenant, unit=unit, start_date=date.today(), agreed_monthly_rent=amount
    )
    return Payment.objects.create(
        tenancy=tenancy,
        amount=amount,
        payment_date=payment_date or date.today(),
        period_start=date.today().replace(day=1),
        period_end=date.today().replace(day=1),
    )


class AmountInWordsTests(TestCase):
    def test_simple_amount(self):
        self.assertEqual(
            amount_in_words(450_000), "Four hundred fifty thousand shillings only"
        )

    def test_small_amount(self):
        self.assertEqual(amount_in_words(1), "One shillings only")


class ReceiptNumberTests(TestCase):
    def test_sequential_numbers_same_year(self):
        payment1 = _make_payment()
        payment2 = _make_payment()
        year = date.today().year
        self.assertEqual(allocate_receipt_number(year), f"RCP-{year}-00001")
        n1 = get_or_create_receipt(payment1).receipt_number
        n2 = get_or_create_receipt(payment2).receipt_number
        self.assertNotEqual(n1, n2)

    def test_get_or_create_is_idempotent(self):
        payment = _make_payment()
        r1 = get_or_create_receipt(payment)
        r2 = get_or_create_receipt(payment)
        self.assertEqual(r1.pk, r2.pk)
        self.assertEqual(r1.receipt_number, r2.receipt_number)

    def test_numbers_restart_per_year(self):
        this_year = date.today().year
        next_year = this_year + 1
        self.assertEqual(allocate_receipt_number(this_year), f"RCP-{this_year}-00001")
        self.assertEqual(allocate_receipt_number(next_year), f"RCP-{next_year}-00001")
        self.assertEqual(allocate_receipt_number(this_year), f"RCP-{this_year}-00002")


@patch("receipts.views.render_receipt_jpg", return_value=b"FAKEJPG")
@patch("receipts.views.render_receipt_pdf", return_value=b"FAKEPDF")
class ReceiptDownloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="landlord", password="pw12345")
        self.client.force_login(self.user)
        self.payment = _make_payment()

    def test_pdf_download(self, mock_pdf, mock_jpg):
        response = self.client.get(reverse("receipt_pdf", args=[self.payment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response.content, b"FAKEPDF")

    def test_jpg_download(self, mock_pdf, mock_jpg):
        response = self.client.get(reverse("receipt_jpg", args=[self.payment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response.content, b"FAKEJPG")

    def test_download_requires_login(self, mock_pdf, mock_jpg):
        self.client.logout()
        response = self.client.get(reverse("receipt_pdf", args=[self.payment.pk]))
        self.assertEqual(response.status_code, 302)


@patch("receipts.views.render_receipt_jpg", return_value=b"FAKEJPG")
@patch("receipts.views.render_receipt_pdf", return_value=b"FAKEPDF")
class PublicReceiptLinkTests(TestCase):
    def setUp(self):
        self.payment = _make_payment()

    def test_valid_token_serves_receipt(self, mock_pdf, mock_jpg):
        token = _signer.sign(str(self.payment.pk))
        response = self.client.get(reverse("public_receipt", args=[token, "pdf"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"FAKEPDF")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_tampered_token_rejected(self, mock_pdf, mock_jpg):
        token = _signer.sign(str(self.payment.pk))
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        response = self.client.get(reverse("public_receipt", args=[tampered, "pdf"]))
        self.assertEqual(response.status_code, 410)

    def test_expired_token_rejected(self, mock_pdf, mock_jpg):
        token = _signer.sign(str(self.payment.pk))
        future = timezone.now() + timedelta(days=31)
        with patch("django.core.signing.time.time", return_value=future.timestamp()):
            response = self.client.get(reverse("public_receipt", args=[token, "pdf"]))
        self.assertEqual(response.status_code, 410)

    def test_nonexistent_payment_token_rejected(self, mock_pdf, mock_jpg):
        token = _signer.sign("999999")
        response = self.client.get(reverse("public_receipt", args=[token, "pdf"]))
        self.assertEqual(response.status_code, 410)
