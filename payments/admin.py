from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("tenancy", "amount", "payment_date", "method", "period_display")
    list_filter = ("method", "payment_date")
    search_fields = ("tenancy__tenant__full_name", "reference")
