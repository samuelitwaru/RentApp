from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("reports/income-expense/", views.income_expense_report, name="reports_income_expense"),
    path(
        "reports/expenses-by-category/",
        views.expenses_by_category_report,
        name="reports_expenses_by_category",
    ),
]
