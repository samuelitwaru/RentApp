from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("", include("tenants.urls")),
    path("", include("payments.urls")),
    path("", include("expenses.urls")),
    path("", include("reports.urls")),
    path("", include("statements.urls")),
    path("", include("receipts.urls")),
]
