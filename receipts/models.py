from django.conf import settings
from django.db import models

from payments.models import Payment


class ReceiptSequence(models.Model):
    """One row per year; guards sequential receipt numbering against races."""

    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)


class Receipt(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField(max_length=20, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.receipt_number


class ReceiptShare(models.Model):
    FORMAT_PDF = "pdf"
    FORMAT_JPG = "jpg"
    FORMAT_CHOICES = [
        (FORMAT_PDF, "PDF"),
        (FORMAT_JPG, "JPG"),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="shares")
    format = models.CharField(max_length=5, choices=FORMAT_CHOICES)
    token = models.TextField(help_text="Signed token for the public receipt link")
    expires_at = models.DateTimeField()
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="receipt_shares"
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-shared_at"]

    def __str__(self):
        return f"{self.payment} ({self.format}) shared {self.shared_at:%Y-%m-%d}"
