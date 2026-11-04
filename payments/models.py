from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from tenants.models import Tenancy


class Payment(models.Model):
    METHOD_CASH = "cash"
    METHOD_MOMO_MTN = "momo_mtn"
    METHOD_MOMO_AIRTEL = "momo_airtel"
    METHOD_BANK = "bank"
    METHOD_OTHER = "other"
    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_MOMO_MTN, "Mobile Money – MTN"),
        (METHOD_MOMO_AIRTEL, "Mobile Money – Airtel"),
        (METHOD_BANK, "Bank"),
        (METHOD_OTHER, "Other"),
    ]

    tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(1)]
    )
    payment_date = models.DateField()
    period_start = models.DateField(help_text="First day of the first month this payment covers")
    period_end = models.DateField(help_text="First day of the last month this payment covers")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="payments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"{self.tenancy.tenant.full_name} - {self.amount} on {self.payment_date}"

    def period_display(self):
        if self.period_start.year == self.period_end.year and (
            self.period_start.month == self.period_end.month
        ):
            return self.period_start.strftime("%b %Y")
        return f"{self.period_start.strftime('%b %Y')} – {self.period_end.strftime('%b %Y')}"
