"""
Purchase reporting — Sprint 5 (Feature Specs: "Purchase Reports").

Mirrors sales_report_service's shape: one base queryset function every
other report filters down from.
"""
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncYear
from django.db.models.functions import Coalesce

from apps.purchases.models import (
    PurchaseItem,
    PurchaseOrder,
    STATUS_CANCELLED,
    STATUS_DRAFT,
    STATUS_ORDERED,
    STATUS_RECEIVED,
)

_TRUNC_FUNCTIONS = {
    "daily": TruncDate,
    "weekly": TruncWeek,
    "monthly": TruncMonth,
    "yearly": TruncYear,
}


def purchase_queryset(*, date_from=None, date_to=None, supplier=None, status=None):
    """Base queryset for every purchase report. `status=None` (the
    default) includes every lifecycle state — Draft, Ordered, Received,
    Cancelled — since 'Purchase Summary' is meant to show the whole
    picture; individual reports narrow it explicitly."""
    qs = PurchaseOrder.objects.select_related("supplier", "created_by")
    if status:
        qs = qs.filter(status=status)
    if supplier:
        qs = qs.filter(supplier=supplier)
    if date_from:
        qs = qs.filter(purchase_date__gte=date_from)
    if date_to:
        qs = qs.filter(purchase_date__lte=date_to)
    return qs


def purchase_summary(*, date_from=None, date_to=None, supplier=None, status=None):
    qs = purchase_queryset(date_from=date_from, date_to=date_to, supplier=supplier, status=status)
    agg = qs.aggregate(
        count=Count("id"),
        total_cost=Coalesce(Sum("grand_total"), Decimal("0")),
        total_subtotal=Coalesce(Sum("subtotal"), Decimal("0")),
    )
    return agg


def purchases_by_supplier(*, date_from=None, date_to=None, status=None):
    """Feature Specs: 'Purchases by Supplier'."""
    qs = purchase_queryset(date_from=date_from, date_to=date_to, status=status)
    return (
        qs.values("supplier__id", "supplier__company_name")
        .annotate(order_count=Count("id"), total_cost=Coalesce(Sum("grand_total"), Decimal("0")))
        .order_by("-total_cost")
    )


def purchases_by_drug(*, date_from=None, date_to=None, status=STATUS_RECEIVED):
    """Feature Specs: 'Purchases by Drug'. Defaults to received orders
    only — Draft/Ordered items haven't actually entered stock yet, so
    including them would overstate what was bought."""
    orders = purchase_queryset(date_from=date_from, date_to=date_to, status=status)
    return (
        PurchaseItem.objects.filter(purchase__in=orders)
        .values("drug__id", "drug__name")
        .annotate(
            quantity=Coalesce(Sum("quantity"), Decimal("0")),
            total_cost=Coalesce(Sum("subtotal"), Decimal("0")),
        )
        .order_by("-total_cost")
    )


def purchases_by_date(*, period="daily", date_from=None, date_to=None, status=None):
    """Feature Specs: 'Purchases by Date'.

    `purchase_date` is already a plain DateField, so for `period="daily"`
    there's nothing to truncate — grouping directly on the field avoids
    an unnecessary Trunc() call (which some backends handle inconsistently
    when applied to a field that's already date-precision). Trunc is only
    used for the genuinely-aggregating periods (week/month/year).
    """
    qs = purchase_queryset(date_from=date_from, date_to=date_to, status=status)
    if period == "daily":
        qs = qs.annotate(period=F("purchase_date"))
    else:
        qs = qs.annotate(period=_TRUNC_FUNCTIONS[period]("purchase_date"))
    return (
        qs.values("period")
        .annotate(count=Count("id"), total_cost=Coalesce(Sum("grand_total"), Decimal("0")))
        .order_by("period")
    )


def received_purchases(*, date_from=None, date_to=None, supplier=None):
    """Feature Specs: 'Received Purchases'."""
    return purchase_queryset(
        date_from=date_from, date_to=date_to, supplier=supplier, status=STATUS_RECEIVED
    )


def cancelled_purchases(*, date_from=None, date_to=None, supplier=None):
    """Feature Specs: 'Cancelled Purchases'."""
    return purchase_queryset(
        date_from=date_from, date_to=date_to, supplier=supplier, status=STATUS_CANCELLED
    )


def outstanding_draft_orders(*, supplier=None):
    """Feature Specs: 'Outstanding Draft Orders' — Draft and Ordered are
    both 'not yet received', so both count as outstanding."""
    qs = PurchaseOrder.objects.select_related("supplier", "created_by").filter(
        status__in=[STATUS_DRAFT, STATUS_ORDERED]
    )
    if supplier:
        qs = qs.filter(supplier=supplier)
    return qs
