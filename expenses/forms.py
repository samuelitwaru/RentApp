from django import forms

from core.forms import BOOTSTRAP_SELECT, BOOTSTRAP_TEXT
from .models import Expense, ExpenseCategory


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "description": forms.Textarea(attrs={**BOOTSTRAP_TEXT, "rows": 2}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["property", "unit", "category", "amount", "date", "description", "vendor", "attachment"]
        widgets = {
            "property": forms.Select(attrs=BOOTSTRAP_SELECT),
            "unit": forms.Select(attrs=BOOTSTRAP_SELECT),
            "category": forms.Select(attrs=BOOTSTRAP_SELECT),
            "amount": forms.NumberInput(attrs=BOOTSTRAP_TEXT),
            "date": forms.DateInput(attrs={**BOOTSTRAP_TEXT, "type": "date"}),
            "description": forms.TextInput(attrs=BOOTSTRAP_TEXT),
            "vendor": forms.TextInput(attrs=BOOTSTRAP_TEXT),
        }
