from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


DEFAULT_RECEIPT_WHATSAPP_TEMPLATE = (
    "Hello {tenant}, thank you for your payment of UGX {amount} for {period}. "
    "Your receipt {receipt_no}: {link}"
)
DEFAULT_STATEMENT_WHATSAPP_TEMPLATE = (
    "Hello {tenant}, view your payment records here: {link} (valid until {expiry})."
)
DEFAULT_LINK_REQUEST_WHATSAPP_TEMPLATE = (
    "Hello, I'd like a new link to view my rent payment records. "
    "Name: {tenant}, Unit: {unit}."
)


class LandlordProfile(models.Model):
    """Singleton: business details, branding and message templates."""

    business_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    phone = PhoneNumberField(blank=True)
    whatsapp_number = PhoneNumberField(
        blank=True,
        help_text="Number tenants reach when requesting a new statement link.",
    )
    logo = models.ImageField(upload_to="landlord/", blank=True, null=True)
    receipt_footer_text = models.CharField(max_length=255, blank=True)

    whatsapp_receipt_template = models.TextField(default=DEFAULT_RECEIPT_WHATSAPP_TEMPLATE)
    whatsapp_statement_template = models.TextField(default=DEFAULT_STATEMENT_WHATSAPP_TEMPLATE)
    whatsapp_link_request_template = models.TextField(
        default=DEFAULT_LINK_REQUEST_WHATSAPP_TEMPLATE
    )

    require_statement_pin = models.BooleanField(
        default=True,
        help_text="Require the last 4 digits of the tenant's phone before showing a statement.",
    )

    class Meta:
        verbose_name = "Landlord profile"

    def __str__(self):
        return self.business_name or "Landlord profile"

    def save(self, *args, **kwargs):
        self.pk = 1
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"business_name": "My Rentals"})
        return obj


class UserProfile(models.Model):
    """Per-login-user details: contact phone and the signature appended to receipts."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    business_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shown on receipts you record payments for, instead of the default business name.",
    )
    phone = PhoneNumberField(blank=True)
    signature = models.ImageField(
        upload_to="signatures/",
        blank=True,
        null=True,
        help_text="Shown above your name on receipts you record payments for.",
    )

    def __str__(self):
        return f"Profile for {self.user}"

    @classmethod
    def get_for_user(cls, user):
        profile, _ = cls.objects.get_or_create(user=user)
        return profile


class Property(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Unit(models.Model):
    STATUS_VACANT = "vacant"
    STATUS_OCCUPIED = "occupied"
    STATUS_CHOICES = [
        (STATUS_VACANT, "Vacant"),
        (STATUS_OCCUPIED, "Occupied"),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    name = models.CharField(max_length=100, help_text="Unit name or number, e.g. 'A1'")
    monthly_rent = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(1)]
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_VACANT)

    class Meta:
        ordering = ["property__name", "name"]
        unique_together = [("property", "name")]

    def __str__(self):
        return f"{self.property.name} - {self.name}"
