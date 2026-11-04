from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Max, Sum


@dataclass
class TenancyBalance:
    months_elapsed: int
    expected_total: Decimal
    paid_total: Decimal
    balance: Decimal  # positive = arrears owed, negative = credit

    @property
    def is_in_arrears(self):
        return self.balance > 0

    @property
    def is_in_credit(self):
        return self.balance < 0

    @property
    def abs_balance(self):
        return abs(self.balance)


def _months_between(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def get_tenancy_balance(tenancy, as_of=None):
    """Expected rent vs payments received for a tenancy, as of a given date."""
    as_of = as_of or date.today()
    end = tenancy.end_date if (tenancy.end_date and tenancy.end_date < as_of) else as_of

    if tenancy.start_date > end:
        months_elapsed = 0
    else:
        months_elapsed = max(_months_between(tenancy.start_date, end), 0)

    expected_total = tenancy.agreed_monthly_rent * months_elapsed
    paid_total = (
        tenancy.payments.filter(payment_date__lte=as_of).aggregate(total=Sum("amount"))["total"]
        or Decimal(0)
    )
    balance = expected_total - paid_total

    return TenancyBalance(
        months_elapsed=months_elapsed,
        expected_total=expected_total,
        paid_total=paid_total,
        balance=balance,
    )


def get_pending_months(tenancy, as_of=None):
    """Calendar months not yet paid for, assuming payments apply to the earliest months first."""
    balance = get_tenancy_balance(tenancy, as_of=as_of)
    if not balance.is_in_arrears or not tenancy.agreed_monthly_rent:
        return []

    arrears_months = min(
        balance.months_elapsed,
        int(-(-balance.balance // tenancy.agreed_monthly_rent)),  # ceiling division
    )
    if arrears_months <= 0:
        return []

    paid_months = balance.months_elapsed - arrears_months
    first_pending = tenancy.start_date + relativedelta(months=paid_months)
    return [(first_pending + relativedelta(months=i)).replace(day=1) for i in range(arrears_months)]


def get_next_period_start(tenancy):
    """First day of the next month not yet covered by a recorded payment."""
    latest_end = tenancy.payments.aggregate(latest=Max("period_end"))["latest"]
    base = latest_end + relativedelta(months=1) if latest_end else tenancy.start_date
    return base.replace(day=1)


def get_tenant_statement_data(tenant):
    """Per-tenancy statement data: tenancy, ordered payments, and current overall balance."""
    data = []
    for tenancy in tenant.tenancies.select_related("unit", "unit__property").all():
        payments = tenancy.payments.select_related("receipt").order_by("-payment_date")
        balance = get_tenancy_balance(tenancy)
        pending_months = get_pending_months(tenancy)
        data.append(
            {
                "tenancy": tenancy,
                "payments": payments,
                "balance": balance,
                "pending_months_display": ", ".join(m.strftime("%b %Y") for m in pending_months),
            }
        )
    return data


def get_tenant_balance(tenant, as_of=None):
    """Aggregate balance across all of a tenant's tenancies."""
    total = Decimal(0)
    for tenancy in tenant.tenancies.all():
        total += get_tenancy_balance(tenancy, as_of=as_of).balance
    return total
