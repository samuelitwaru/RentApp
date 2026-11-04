from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def ugx(value):
    """Format an amount as 'UGX 450,000' (no decimals, comma thousands separators)."""
    if value in (None, ""):
        return ""
    try:
        amount = int(Decimal(value).to_integral_value())
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"UGX {amount:,}"
