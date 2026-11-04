from django.urls import path

from . import views

urlpatterns = [
    path("expenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("expenses/new/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("expenses/<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="expense_delete"),
    path("expense-categories/", views.ExpenseCategoryListView.as_view(), name="expense_category_list"),
    path(
        "expense-categories/new/",
        views.ExpenseCategoryCreateView.as_view(),
        name="expense_category_create",
    ),
    path(
        "expense-categories/<int:pk>/edit/",
        views.ExpenseCategoryUpdateView.as_view(),
        name="expense_category_edit",
    ),
    path(
        "expense-categories/<int:pk>/delete/",
        views.ExpenseCategoryDeleteView.as_view(),
        name="expense_category_delete",
    ),
]
