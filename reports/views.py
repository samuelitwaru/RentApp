import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render

from core.models import Unit
from expenses.models import Expense
from payments.models import Payment
from statements.models import LinkRequest
from tenants.models import Tenancy
from tenants.services import get_tenancy_balance


@login_required
def dashboard(request):
    today = date.today()

    collected_this_month = (
        Payment.objects.filter(
            payment_date__year=today.year, payment_date__month=today.month
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    expenses_this_month = (
        Expense.objects.filter(date__year=today.year, date__month=today.month).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    net_income = collected_this_month - expenses_this_month

    total_units = Unit.objects.count()
    occupied_units = Unit.objects.filter(status=Unit.STATUS_OCCUPIED).count()
    occupancy_rate = round((occupied_units / total_units) * 100, 1) if total_units else 0

    outstanding = []
    for tenancy in Tenancy.objects.filter(is_active=True).select_related(
        "tenant", "unit", "unit__property"
    ):
        balance = get_tenancy_balance(tenancy)
        if balance.is_in_arrears:
            outstanding.append((tenancy, balance))

    context = {
        "collected_this_month": collected_this_month,
        "expenses_this_month": expenses_this_month,
        "net_income": net_income,
        "occupancy_rate": occupancy_rate,
        "occupied_units": occupied_units,
        "total_units": total_units,
        "outstanding": outstanding,
        "recent_payments": Payment.objects.select_related("tenancy__tenant")[:5],
        "recent_expenses": Expense.objects.select_related("property")[:5],
        "pending_link_requests": LinkRequest.objects.filter(handled=False).select_related("tenant"),
    }
    return render(request, "reports/dashboard.html", context)


def _filtered(queryset, request, date_field):
    params = request.GET
    if params.get("date_from"):
        queryset = queryset.filter(**{f"{date_field}__gte": params["date_from"]})
    if params.get("date_to"):
        queryset = queryset.filter(**{f"{date_field}__lte": params["date_to"]})
    if params.get("property"):
        queryset = queryset.filter(**{_property_lookup(queryset): params["property"]})
    return queryset


def _property_lookup(queryset):
    return "property_id" if queryset.model.__name__ == "Expense" else "tenancy__unit__property_id"


@login_required
def income_expense_report(request):
    payments = _filtered(Payment.objects.all(), request, "payment_date")
    expenses = _filtered(Expense.objects.all(), request, "date")

    by_month = {}
    for p in payments:
        key = p.payment_date.strftime("%Y-%m")
        by_month.setdefault(key, {"income": 0, "expenses": 0})
        by_month[key]["income"] += p.amount
    for e in expenses:
        key = e.date.strftime("%Y-%m")
        by_month.setdefault(key, {"income": 0, "expenses": 0})
        by_month[key]["expenses"] += e.amount
    for row in by_month.values():
        row["net"] = row["income"] - row["expenses"]

    by_property = {}
    for p in payments.select_related("tenancy__unit__property"):
        key = p.tenancy.unit.property.name
        by_property.setdefault(key, {"income": 0, "expenses": 0})
        by_property[key]["income"] += p.amount
    for e in expenses.select_related("property"):
        key = e.property.name
        by_property.setdefault(key, {"income": 0, "expenses": 0})
        by_property[key]["expenses"] += e.amount

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="income_expense_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Month", "Income", "Expenses", "Net"])
        for month in sorted(by_month):
            row = by_month[month]
            writer.writerow([month, row["income"], row["expenses"], row["income"] - row["expenses"]])
        return response

    from core.models import Property

    context = {
        "by_month": sorted(by_month.items()),
        "by_property": sorted(by_property.items()),
        "properties": Property.objects.all(),
    }
    return render(request, "reports/income_expense.html", context)


@login_required
def expenses_by_category_report(request):
    expenses = _filtered(Expense.objects.select_related("category"), request, "date")
    by_category = {}
    for e in expenses:
        key = e.category.name
        by_category[key] = by_category.get(key, 0) + e.amount

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses_by_category.csv"'
        writer = csv.writer(response)
        writer.writerow(["Category", "Total"])
        for category, total in sorted(by_category.items()):
            writer.writerow([category, total])
        return response

    context = {"by_category": sorted(by_category.items())}
    return render(request, "reports/expenses_by_category.html", context)
