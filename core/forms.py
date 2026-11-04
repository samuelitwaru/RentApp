from django import forms
from django.contrib.auth import get_user_model

from .models import LandlordProfile, Property, Unit, UserProfile

BOOTSTRAP_TEXT = {"class": "form-control"}
BOOTSTRAP_CHECK = {"class": "form-check-input"}
BOOTSTRAP_SELECT = {"class": "form-select"}

User = get_user_model()


class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "last_name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "email": forms.EmailInput(attrs=BOOTSTRAP_TEXT),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["business_name", "phone", "signature"]
        widgets = {
            "business_name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "phone": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "signature": forms.ClearableFileInput(attrs=BOOTSTRAP_TEXT),
        }


class LandlordProfileForm(forms.ModelForm):
    class Meta:
        model = LandlordProfile
        fields = [
            "business_name",
            "address",
            "phone",
            "whatsapp_number",
            "logo",
            "receipt_footer_text",
            "whatsapp_receipt_template",
            "whatsapp_statement_template",
            "whatsapp_link_request_template",
            "require_statement_pin",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "address": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "receipt_footer_text": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "whatsapp_receipt_template": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 3}),
            "whatsapp_statement_template": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 3}),
            "whatsapp_link_request_template": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 3}),
            "require_statement_pin": forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
        }


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ["name", "location", "notes"]
        widgets = {
            "name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "location": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "notes": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 3}),
        }


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name", "monthly_rent", "status"]
        widgets = {
            "name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "monthly_rent": forms.NumberInput(attrs=BOOTSTRAP_TEXT),
            "status": forms.Select(attrs=BOOTSTRAP_SELECT),
        }
