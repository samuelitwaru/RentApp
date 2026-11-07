from django.urls import path

from . import views

urlpatterns = [
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("payments/new/", views.PaymentCreateView.as_view(), name="payment_create"),
    path(
        "payments/receipts/zip/",
        views.PaymentBulkReceiptZipView.as_view(),
        name="payment_bulk_receipts_zip",
    ),
    path("payments/<int:pk>/", views.PaymentDetailView.as_view(), name="payment_detail"),
    path("payments/<int:pk>/edit/", views.PaymentUpdateView.as_view(), name="payment_edit"),
    path("payments/<int:pk>/delete/", views.PaymentDeleteView.as_view(), name="payment_delete"),
]
