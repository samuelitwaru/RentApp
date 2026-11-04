from django.contrib import admin

from .models import LinkRequest, TenantAccessLink


@admin.register(TenantAccessLink)
class TenantAccessLinkAdmin(admin.ModelAdmin):
    list_display = ("tenant", "created_at", "expires_at", "revoked", "access_count")
    list_filter = ("revoked",)
    search_fields = ("tenant__full_name",)


@admin.register(LinkRequest)
class LinkRequestAdmin(admin.ModelAdmin):
    list_display = ("tenant", "requested_at", "handled", "handled_at")
    list_filter = ("handled",)
