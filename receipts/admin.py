from django.contrib import admin

from .models import Receipt, ReceiptShare


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "payment", "issued_at")
    search_fields = ("receipt_number",)


@admin.register(ReceiptShare)
class ReceiptShareAdmin(admin.ModelAdmin):
    list_display = ("payment", "format", "shared_by", "shared_at", "expires_at")
    list_filter = ("format",)
