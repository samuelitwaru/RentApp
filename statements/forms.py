from django import forms

from core.forms import BOOTSTRAP_CHECK, BOOTSTRAP_SELECT, BOOTSTRAP_TEXT

EXPIRY_24H = "24h"
EXPIRY_7D = "7d"
EXPIRY_30D = "30d"
EXPIRY_CUSTOM = "custom"

EXPIRY_CHOICES = [
    (EXPIRY_24H, "24 hours"),
    (EXPIRY_7D, "7 days"),
    (EXPIRY_30D, "30 days"),
    (EXPIRY_CUSTOM, "Custom date/time"),
]


class AccessLinkCreateForm(forms.Form):
    expiry_choice = forms.ChoiceField(
        choices=EXPIRY_CHOICES, widget=forms.Select(attrs=BOOTSTRAP_SELECT)
    )
    custom_expiry = forms.DateTimeField(
        required=False, widget=forms.DateTimeInput(attrs={**BOOTSTRAP_TEXT, "type": "datetime-local"})
    )
    revoke_others = forms.BooleanField(
        required=False,
        label="Revoke other active links for this tenant",
        widget=forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("expiry_choice") == EXPIRY_CUSTOM and not cleaned.get("custom_expiry"):
            self.add_error("custom_expiry", "Required when 'Custom date/time' is selected.")
        return cleaned


class StatementPinForm(forms.Form):
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        label="Last 4 digits of your phone number",
        widget=forms.TextInput(
            attrs={**BOOTSTRAP_TEXT, "inputmode": "numeric", "autocomplete": "off"}
        ),
    )
