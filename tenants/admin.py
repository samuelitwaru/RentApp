from django.contrib import admin

from .models import Tenancy, Tenant


class TenancyInline(admin.TabularInline):
    model = Tenancy
    extra = 0


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email")
    search_fields = ("full_name", "phone", "email", "national_id")
    inlines = [TenancyInline]


@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = ("tenant", "unit", "start_date", "end_date", "agreed_monthly_rent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("tenant__full_name", "unit__name")
