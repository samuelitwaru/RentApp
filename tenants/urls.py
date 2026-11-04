from django.urls import path

from . import views

urlpatterns = [
    path("tenants/", views.TenantListView.as_view(), name="tenant_list"),
    path("tenants/new/", views.TenantCreateView.as_view(), name="tenant_create"),
    path("tenants/<int:pk>/", views.TenantDetailView.as_view(), name="tenant_detail"),
    path("tenants/<int:pk>/edit/", views.TenantUpdateView.as_view(), name="tenant_edit"),
    path("tenants/<int:pk>/delete/", views.TenantDeleteView.as_view(), name="tenant_delete"),
    path("tenancies/new/", views.TenancyCreateView.as_view(), name="tenancy_create"),
    path("tenancies/<int:pk>/edit/", views.TenancyUpdateView.as_view(), name="tenancy_edit"),
    path("tenancies/<int:pk>/delete/", views.TenancyDeleteView.as_view(), name="tenancy_delete"),
]
