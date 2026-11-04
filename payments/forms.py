from django import forms

from core.forms import BOOTSTRAP_CHECK, BOOTSTRAP_SELECT, BOOTSTRAP_TEXT
from .models import Payment


class PaymentForm(forms.ModelForm):
    confirm_inactive = forms.BooleanField(
        required=False,
        label="Record anyway (this tenancy is inactive)",
        widget=forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
    )

    class Meta:
        model = Payment
        fields = [
            "tenancy",
            "amount",
            "payment_date",
            "period_start",
            "period_end",
            "method",
            "reference",
            "notes",
        ]
        widgets = {
            "tenancy": forms.Select(attrs=BOOTSTRAP_SELECT),
            "amount": forms.NumberInput(attrs=BOOTSTRAP_TEXT),
            "payment_date": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "period_start": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "period_end": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "method": forms.Select(attrs=BOOTSTRAP_SELECT),
            "reference": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "notes": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("period_start"), cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "Period end cannot be before period start.")
        return cleaned
