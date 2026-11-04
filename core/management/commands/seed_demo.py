import random
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import LandlordProfile, Property, Unit
from expenses.models import Expense, ExpenseCategory
from payments.models import Payment
from receipts.services import get_or_create_receipt
from tenants.models import Tenancy, Tenant

DEMO_TAG = "[seed_demo]"


class Command(BaseCommand):
    help = "Create sample properties, units, tenants, tenancies, payments and expenses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before creating new data.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        with transaction.atomic():
            self._seed_landlord_profile()
            self._seed_login_user()
            properties = self._seed_properties_and_units()
            tenants = self._seed_tenants()
            tenancies = self._seed_tenancies(tenants, properties)
            self._seed_payments(tenancies)
            self._seed_expenses(properties)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _flush(self):
        Payment.objects.filter(notes__contains=DEMO_TAG).delete()
        Expense.objects.filter(description__contains=DEMO_TAG).delete()
        Tenancy.objects.filter(tenant__notes__contains=DEMO_TAG).delete()
        Tenant.objects.filter(notes__contains=DEMO_TAG).delete()
        Unit.objects.filter(property__notes__contains=DEMO_TAG).delete()
        Property.objects.filter(notes__contains=DEMO_TAG).delete()
        self.stdout.write("Flushed previous demo data.")

    def _seed_landlord_profile(self):
        profile = LandlordProfile.get_solo()
        profile.business_name = profile.business_name or "Kampala Rentals Ltd"
        profile.address = profile.address or "Plot 12, Kira Road, Kampala"
        profile.phone = profile.phone or "+256772000000"
        profile.whatsapp_number = profile.whatsapp_number or "+256772000000"
        profile.receipt_footer_text = profile.receipt_footer_text or "Thank you for your business."
        profile.save()

    def _seed_login_user(self):
        User = get_user_model()
        if not User.objects.filter(username="landlord").exists():
            User.objects.create_superuser(
                username="landlord", email="landlord@example.com", password="changeme123"
            )
            self.stdout.write(
                self.style.WARNING(
                    "Created login user 'landlord' / 'changeme123' — change this password."
                )
            )

    def _seed_properties_and_units(self):
        properties_spec = [
            ("Kira Road Apartments", "Kira Road, Kampala", 4, 450_000),
            ("Ntinda Court", "Ntinda, Kampala", 3, 600_000),
        ]
        properties = []
        for name, location, unit_count, base_rent in properties_spec:
            prop, _ = Property.objects.get_or_create(
                name=name, defaults={"location": location, "notes": DEMO_TAG}
            )
            units = []
            for i in range(1, unit_count + 1):
                unit, _ = Unit.objects.get_or_create(
                    property=prop,
                    name=f"A{i}",
                    defaults={
                        "monthly_rent": base_rent + (i * 25_000),
                        "status": Unit.STATUS_VACANT,
                    },
                )
                units.append(unit)
            properties.append((prop, units))
        return properties

    def _seed_tenants(self):
        names = [
            "Grace Nakimuli",
            "Daniel Okello",
            "Esther Atuhaire",
            "Moses Ssentamu",
            "Patience Auma",
        ]
        tenants = []
        for i, name in enumerate(names):
            tenant, _ = Tenant.objects.get_or_create(
                full_name=name,
                defaults={
                    "phone": f"+25677{1000000 + i * 111:07d}",
                    "email": f"{name.split()[0].lower()}@example.com",
                    "notes": DEMO_TAG,
                },
            )
            tenants.append(tenant)
        return tenants

    def _seed_tenancies(self, tenants, properties):
        all_units = [unit for _, units in properties for unit in units]
        tenancies = []
        start = date.today() - relativedelta(months=6)
        for tenant, unit in zip(tenants, all_units):
            tenancy, created = Tenancy.objects.get_or_create(
                tenant=tenant,
                unit=unit,
                defaults={
                    "start_date": start,
                    "agreed_monthly_rent": unit.monthly_rent,
                    "deposit_amount": unit.monthly_rent,
                    "is_active": True,
                },
            )
            if created:
                unit.status = Unit.STATUS_OCCUPIED
                unit.save()
            tenancies.append(tenancy)
        return tenancies

    def _seed_payments(self, tenancies):
        methods = [m for m, _ in Payment.METHOD_CHOICES]
        today = date.today()
        for idx, tenancy in enumerate(tenancies):
            months_to_pay = 6 if idx != len(tenancies) - 1 else 4  # leave one tenant in arrears
            for m in range(months_to_pay):
                period = (today - relativedelta(months=months_to_pay - 1 - m)).replace(day=1)
                payment, _ = Payment.objects.get_or_create(
                    tenancy=tenancy,
                    period_start=period,
                    period_end=period,
                    defaults={
                        "amount": tenancy.agreed_monthly_rent,
                        "payment_date": period + timedelta(days=random.randint(0, 5)),
                        "method": methods[(idx + m) % len(methods)],
                        "reference": f"DEMO-{idx}-{m}",
                        "notes": DEMO_TAG,
                    },
                )
                get_or_create_receipt(payment)

    def _seed_expenses(self, properties):
        categories = list(ExpenseCategory.objects.all())
        today = date.today()
        for prop, units in properties:
            for m in range(3):
                category = categories[(m + prop.pk) % len(categories)]
                Expense.objects.get_or_create(
                    property=prop,
                    date=(today - relativedelta(months=m)).replace(day=5),
                    description=f"{category.name} for {prop.name} {DEMO_TAG}",
                    defaults={
                        "category": category,
                        "amount": Decimal(random.choice([50_000, 80_000, 120_000, 200_000])),
                        "vendor": "Demo Vendor Ltd",
                    },
                )
