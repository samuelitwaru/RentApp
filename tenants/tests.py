from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.test import TestCase

from core.models import Property, Unit
from payments.models import Payment
from tenants.models import Tenancy, Tenant
from tenants.services import get_tenancy_balance


class TenancyBalanceTests(TestCase):
    def setUp(self):
        prop = Property.objects.create(name="Test Property")
        self.unit = Unit.objects.create(property=prop, name="A1", monthly_rent=300_000)
        self.tenant = Tenant.objects.create(full_name="Jane Doe", phone="+256772000111")

    def test_arrears_when_no_payments(self):
        start = date.today() - relativedelta(months=2)
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=start, agreed_monthly_rent=300_000
        )
        balance = get_tenancy_balance(tenancy)
        self.assertEqual(balance.months_elapsed, 3)
        self.assertEqual(balance.expected_total, Decimal(900_000))
        self.assertEqual(balance.paid_total, Decimal(0))
        self.assertTrue(balance.is_in_arrears)
        self.assertEqual(balance.balance, Decimal(900_000))

    def test_credit_when_overpaid(self):
        start = date.today().replace(day=1)
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=start, agreed_monthly_rent=300_000
        )
        Payment.objects.create(
            tenancy=tenancy,
            amount=600_000,
            payment_date=date.today(),
            period_start=start,
            period_end=start,
        )
        balance = get_tenancy_balance(tenancy)
        self.assertEqual(balance.months_elapsed, 1)
        self.assertTrue(balance.is_in_credit)
        self.assertEqual(balance.balance, Decimal(-300_000))

    def test_as_of_ignores_payments_made_after_that_date(self):
        start = date.today() - relativedelta(months=2)
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=start, agreed_monthly_rent=300_000
        )
        earlier_date = start
        later_date = date.today()
        Payment.objects.create(
            tenancy=tenancy,
            amount=600_000,
            payment_date=earlier_date,
            period_start=earlier_date,
            period_end=earlier_date,
        )
        Payment.objects.create(
            tenancy=tenancy,
            amount=600_000,
            payment_date=later_date,
            period_start=later_date,
            period_end=later_date,
        )
        balance = get_tenancy_balance(tenancy, as_of=earlier_date)
        self.assertEqual(balance.paid_total, Decimal(600_000))


class PhoneNormalisationTests(TestCase):
    def test_local_format_normalised_to_e164(self):
        tenant = Tenant.objects.create(full_name="Local Format", phone="0772123456")
        tenant.refresh_from_db()
        self.assertEqual(str(tenant.phone), "+256772123456")

    def test_spaced_format_normalised_to_e164(self):
        tenant = Tenant.objects.create(full_name="Spaced Format", phone="0772 123 456")
        tenant.refresh_from_db()
        self.assertEqual(str(tenant.phone), "+256772123456")
