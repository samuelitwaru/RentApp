from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("settings/", views.LandlordSettingsView.as_view(), name="landlord_settings"),
    path("properties/", views.PropertyListView.as_view(), name="property_list"),
    path("properties/new/", views.PropertyCreateView.as_view(), name="property_create"),
    path("properties/<int:pk>/", views.PropertyDetailView.as_view(), name="property_detail"),
    path("properties/<int:pk>/edit/", views.PropertyUpdateView.as_view(), name="property_edit"),
    path("properties/<int:pk>/delete/", views.PropertyDeleteView.as_view(), name="property_delete"),
    path(
        "properties/<int:property_pk>/units/new/",
        views.UnitCreateView.as_view(),
        name="unit_create",
    ),
    path("units/<int:pk>/edit/", views.UnitUpdateView.as_view(), name="unit_edit"),
    path("units/<int:pk>/delete/", views.UnitDeleteView.as_view(), name="unit_delete"),
]
