from django.core.validators import MinValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from core.models import Unit


class Tenant(models.Model):
    full_name = models.CharField(max_length=255)
    phone = PhoneNumberField()
    email = models.EmailField(blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Tenancy(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tenancies")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="tenancies")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    agreed_monthly_rent = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(1)]
    )
    deposit_amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "tenancies"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.tenant.full_name} @ {self.unit}"
