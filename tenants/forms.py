from django import forms

from core.forms import BOOTSTRAP_SELECT, BOOTSTRAP_TEXT
from .models import Tenancy, Tenant


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["full_name", "phone", "email", "national_id", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "email": forms.EmailInput(attrs=BOOTSTRAP_TEXT),
            "national_id": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "notes": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 3}),
        }


class TenancyForm(forms.ModelForm):
    class Meta:
        model = Tenancy
        fields = ["tenant", "unit", "start_date", "end_date", "agreed_monthly_rent", "deposit_amount", "is_active"]
        widgets = {
            "tenant": forms.Select(attrs=BOOTSTRAP_SELECT),
            "unit": forms.Select(attrs=BOOTSTRAP_SELECT),
            "start_date": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "end_date": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "agreed_monthly_rent": forms.NumberInput(attrs=BOOTSTRAP_TEXT),
            "deposit_amount": forms.NumberInput(attrs=BOOTSTRAP_TEXT),
        }
