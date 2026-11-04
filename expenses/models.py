from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import Property, Unit

DEFAULT_CATEGORIES = [
    ("Repairs & Maintenance", ""),
    ("Utilities", ""),
    ("Property Tax/Rates", ""),
    ("Security", ""),
    ("Cleaning", ""),
    ("Insurance", ""),
    ("Agent/Commission", ""),
    ("Legal", ""),
    ("Other", ""),
]


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "expense categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="expenses")
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.PROTECT, related_name="expenses"
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(1)]
    )
    date = models.DateField()
    description = models.CharField(max_length=255)
    vendor = models.CharField(max_length=255, blank=True, verbose_name="Vendor/payee")
    attachment = models.FileField(upload_to="expenses/", blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="expenses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.description} - {self.amount}"
