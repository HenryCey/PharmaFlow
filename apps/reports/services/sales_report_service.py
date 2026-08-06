"""
Sales reporting — Sprint 5 (Feature Specs: "Sales Reports").

`sales_queryset()` is the single entry point every other function in
this module (and dashboard_service) filters down from, so row-level
scoping and the "completed sales only" default are enforced in exactly
one place — per the Sprint 5 brief's reporting-architecture instruction.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncWeek, TruncYear
from django.utils import timezone

from apps.sales.models import STATUS_COMPLETED, Sale, SaleItem
from apps.sales.sales_service import get_sales_queryset

_TRUNC_FUNCTIONS = {
    "daily": TruncDate,
    "weekly": TruncWeek,
    "monthly": TruncMonth,
    "yearly": TruncYear,
}


def _line_total():
    return ExpressionWrapper(
        F("quantity") * F("unit_price") - F("discount"),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )


def sales_queryset(*, date_from=None, date_to=None, cashier=None, customer=None,
                    status=STATUS_COMPLETED, user=None):
    """
    Base queryset for every sales report. `status=STATUS_COMPLETED` by
    default, matching apps/sales/sales_service.py:daily_sales_summary's
    existing convention — pass status=None to include cancelled sales too
    (e.g. for a full Receipt History).

    `user`, when given, applies the same row-level scoping Sales History
    already uses (Cashiers see only their own sales) by reusing
    get_sales_queryset rather than re-implementing the permission check.
    """
    qs = get_sales_queryset(user) if user is not None else Sale.objects.select_related(
        "customer", "cashier"
    )
    if status is not None:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if cashier:
        qs = qs.filter(cashier=cashier)
    if customer:
        qs = qs.filter(customer=customer)
    return qs


def sales_summary(*, date_from=None, date_to=None, cashier=None, customer=None, user=None):
    qs = sales_queryset(
        date_from=date_from, date_to=date_to, cashier=cashier, customer=customer, user=user
    )
    agg = qs.aggregate(
        count=Count("id"),
        revenue=Coalesce(Sum("total"), Decimal("0")),
        discount_given=Coalesce(Sum("discount"), Decimal("0")),
    )
    return agg


def sales_trend(*, period="daily", date_from=None, date_to=None, user=None):
    """Feature Specs: 'Daily / Weekly / Monthly / Yearly Sales'. One
    function, parameterized by period, instead of four near-identical
    ones."""
    trunc = _TRUNC_FUNCTIONS[period]
    qs = sales_queryset(date_from=date_from, date_to=date_to, user=user)
    return (
        qs.annotate(period=trunc("created_at"))
        .values("period")
        .annotate(revenue=Coalesce(Sum("total"), Decimal("0")), count=Count("id"))
        .order_by("period")
    )


def sales_by_drug(*, date_from=None, date_to=None, user=None, limit=None):
    """Feature Specs: 'Sales by Drug'."""
    sales = sales_queryset(date_from=date_from, date_to=date_to, user=user)
    # `revenue` is annotated *before* `quantity` deliberately: `revenue`'s
    # expression references F("quantity") internally (via _line_total()),
    # and SaleItem already has a real `quantity` field. If a `quantity`
    # annotation existed on the query first, Django would resolve that
    # inner F("quantity") against the new *annotation* (itself a Sum, i.e.
    # an aggregate) instead of the real field, and raise "is an aggregate"
    # — reproduced and confirmed while verifying this module. Annotating
    # in this order sidesteps it entirely.
    qs = (
        SaleItem.objects.filter(sale__in=sales)
        .values("drug__id", "drug__name")
        .annotate(
            revenue=Coalesce(Sum(_line_total()), Decimal("0")),
            quantity=Coalesce(Sum("quantity"), Decimal("0")),
        )
        .order_by("-revenue")
    )
    return qs[:limit] if limit else qs


def sales_by_customer(*, date_from=None, date_to=None, user=None):
    """Feature Specs: 'Sales by Customer'. Walk-in sales (customer is
    null) are grouped together, matching how the rest of the app treats
    a null Sale.customer as 'walk-in', not as missing data."""
    qs = sales_queryset(date_from=date_from, date_to=date_to, user=user)
    return (
        qs.values("customer__id", "customer__name")
        .annotate(count=Count("id"), revenue=Coalesce(Sum("total"), Decimal("0")))
        .order_by("-revenue")
    )


def sales_by_cashier(*, date_from=None, date_to=None):
    """Feature Specs: 'Sales by User (Cashier)'. Deliberately does not
    accept `user=` scoping — this report itself is management-facing
    (a Cashier viewing their own sales already has Sales History /
    Today's Sales), gated at the view layer by view_sales_reports."""
    qs = sales_queryset(date_from=date_from, date_to=date_to)
    return (
        qs.values("cashier__id", "cashier__username", "cashier__first_name", "cashier__last_name")
        .annotate(count=Count("id"), revenue=Coalesce(Sum("total"), Decimal("0")))
        .order_by("-revenue")
    )


def top_selling_drugs(*, limit=10, date_from=None, date_to=None, user=None):
    return sales_by_drug(date_from=date_from, date_to=date_to, user=user, limit=None).order_by(
        "-quantity"
    )[:limit]


def slow_moving_drugs(*, days=30, limit=10):
    """
    Feature Specs: 'Slow Moving Drugs' — drugs with stock on hand but
    little/no sales activity in the trailing window. Uses a filtered
    annotation (not a Python-side merge) so it scales the same way the
    rest of this module's aggregations do.
    """
    from django.db.models import Q

    from apps.inventory.models import Drug

    cutoff = timezone.now() - timedelta(days=days)
    return (
        Drug.objects.filter(current_stock__gt=0)
        .annotate(
            quantity_sold=Coalesce(
                Sum(
                    "sale_items__quantity",
                    filter=Q(
                        sale_items__sale__status=STATUS_COMPLETED,
                        sale_items__sale__created_at__gte=cutoff,
                    ),
                ),
                Decimal("0"),
            )
        )
        .order_by("quantity_sold", "name")[:limit]
    )


def receipt_history(*, date_from=None, date_to=None, cashier=None, customer=None, user=None):
    """Feature Specs: 'Receipt History' — every sale including cancelled
    ones, since a cancelled sale's receipt is still part of the history."""
    return sales_queryset(
        date_from=date_from, date_to=date_to, cashier=cashier, customer=customer,
        status=None, user=user,
    )
