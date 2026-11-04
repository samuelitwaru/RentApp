from django.urls import path

from . import views

urlpatterns = [
    path(
        "tenants/<int:pk>/statement/",
        views.TenantStatementView.as_view(),
        name="tenant_statement",
    ),
    path(
        "tenants/<int:tenant_pk>/access-links/new/",
        views.AccessLinkCreateView.as_view(),
        name="access_link_create",
    ),
    path("access-links/<int:pk>/revoke/", views.revoke_access_link, name="access_link_revoke"),
    path("link-requests/<int:pk>/handle/", views.handle_link_request, name="handle_link_request"),
    path("statement/<str:token>/", views.public_statement_view, name="public_statement"),
    path(
        "statement/<str:token>/receipt/<int:payment_pk>/<str:fmt>/",
        views.public_statement_receipt,
        name="public_statement_receipt",
    ),
    path(
        "statement/<str:token>/request-new-link/",
        views.request_new_link,
        name="request_new_link",
    ),
]
