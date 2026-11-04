from django.urls import path

from . import views

urlpatterns = [
    path("payments/<int:pk>/receipt/pdf/", views.download_receipt_pdf, name="receipt_pdf"),
    path("payments/<int:pk>/receipt/jpg/", views.download_receipt_jpg, name="receipt_jpg"),
    path(
        "payments/<int:pk>/share/whatsapp/<str:fmt>/",
        views.share_receipt_whatsapp,
        name="receipt_share_whatsapp",
    ),
    path("r/<str:token>/<str:fmt>/", views.public_receipt_view, name="public_receipt"),
]
