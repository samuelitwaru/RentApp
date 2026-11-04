from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Property

from .models import DEFAULT_CATEGORIES, Expense, ExpenseCategory


class DefaultCategoriesTests(TestCase):
    def test_default_categories_seeded_by_migration(self):
        names = set(ExpenseCategory.objects.values_list("name", flat=True))
        for name, _ in DEFAULT_CATEGORIES:
            self.assertIn(name, names)


class ExpenseValidationTests(TestCase):
    def setUp(self):
        self.property = Property.objects.create(name="Test Property")
        self.category = ExpenseCategory.objects.first()

    def test_negative_amount_rejected(self):
        expense = Expense(
            property=self.property,
            category=self.category,
            amount=-1,
            date=date.today(),
            description="Broken pipe",
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_description_required(self):
        expense = Expense(
            property=self.property,
            category=self.category,
            amount=50_000,
            date=date.today(),
            description="",
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()
