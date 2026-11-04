from django.contrib import admin

from .models import LandlordProfile, Property, Unit, UserProfile


@admin.register(LandlordProfile)
class LandlordProfileAdmin(admin.ModelAdmin):
    list_display = ("business_name", "phone", "whatsapp_number")

    def has_add_permission(self, request):
        return not LandlordProfile.objects.exists()


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "user__first_name", "user__last_name")


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "location")
    search_fields = ("name", "location")
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("property", "name", "monthly_rent", "status")
    list_filter = ("status", "property")
    search_fields = ("name", "property__name")
