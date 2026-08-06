"""
Inventory reporting — Sprint 5 (Feature Specs: "Inventory Reports").

Every query here reads from apps/inventory (the catalog) and
apps/stock (the ledger) — it never writes to either. Where a query
already exists elsewhere (e.g. Low Stock), it's imported and reused
rather than re-implemented, per the Sprint 5 brief's "avoid duplicated
queries and duplicated business logic" instruction.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import Drug
from apps.inventory.services import low_stock_drugs as _low_stock_drugs
from apps.purchases.models import PurchaseItem, STATUS_RECEIVED
from apps.stock.models import InventoryMovement, StockAdjustment


def _money(expression):
    """Wraps a quantity*price style expression with the DecimalField
    output_field every stored money field in this project uses, so every
    aggregation below stays a single readable line."""
    return ExpressionWrapper(expression, output_field=DecimalField(max_digits=16, decimal_places=2))


def current_inventory(*, category=None, search=None, status=None):
    """Full catalog with current stock — Feature Specs: 'Current Inventory Report'."""
    qs = Drug.objects.select_related("category", "manufacturer", "unit")
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs


def inventory_valuation(*, category=None):
    """Feature Specs: 'Inventory Valuation Report'. Cost value uses
    Drug.cost_price (the current, Last-Cost-Wins catalog price — see
    FUTURE_ENHANCEMENTS_BACKLOG PFE-010 for the documented limitation
    that this is not FIFO/weighted-average costed)."""
    qs = Drug.objects.all()
    if category:
        qs = qs.filter(category=category)

    agg = qs.aggregate(
        drug_count=Count("id"),
        total_quantity=Coalesce(Sum("current_stock"), Decimal("0")),
        total_cost_value=Coalesce(
            Sum(_money(F("current_stock") * F("cost_price"))), Decimal("0")
        ),
        total_retail_value=Coalesce(
            Sum(_money(F("current_stock") * F("selling_price"))), Decimal("0")
        ),
    )
    return agg


def low_stock_drugs(*, category=None):
    """Reuses apps.inventory.services.low_stock_drugs — the same rule
    already used by the Drug list's Low Stock filter."""
    qs = Drug.objects.select_related("category", "unit")
    if category:
        qs = qs.filter(category=category)
    return _low_stock_drugs(qs)


def out_of_stock_drugs(*, category=None):
    qs = Drug.objects.select_related("category", "unit").filter(current_stock__lte=0)
    if category:
        qs = qs.filter(category=category)
    return qs


def near_expiry_drugs(*, days=30):
    """
    Feature Specs: 'Expiry Alerts' / 'Near Expiry Drugs'.

    Documented limitation: PharmaFlow tracks expiry per received
    PurchaseItem batch, not per remaining unit of stock (no FEFO ledger
    — FUTURE_ENHANCEMENTS_BACKLOG PFE-002 is exactly this, deferred to
    v2.x+). This surfaces any drug that still has stock on hand AND has
    at least one received batch expiring within `days` — a per-drug
    signal, not a guarantee that the *specific* units on the shelf are
    the expiring batch.
    """
    today = timezone.localdate()
    threshold = today + timedelta(days=days)
    drug_ids = (
        PurchaseItem.objects.filter(
            purchase__status=STATUS_RECEIVED,
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=threshold,
        )
        .values_list("drug_id", flat=True)
        .distinct()
    )
    return Drug.objects.select_related("category", "unit").filter(
        id__in=list(drug_ids), current_stock__gt=0
    )


def expired_drugs():
    """Same per-drug approximation as near_expiry_drugs, for batches
    already past expiry_date."""
    today = timezone.localdate()
    drug_ids = (
        PurchaseItem.objects.filter(
            purchase__status=STATUS_RECEIVED,
            expiry_date__isnull=False,
            expiry_date__lt=today,
        )
        .values_list("drug_id", flat=True)
        .distinct()
    )
    return Drug.objects.select_related("category", "unit").filter(
        id__in=list(drug_ids), current_stock__gt=0
    )


def batch_report(*, drug=None, supplier=None, date_from=None, date_to=None):
    """Feature Specs: 'Batch Report' — every received PurchaseItem, which
    is where batch/expiry data actually lives (Drug itself carries none,
    by the original Database Spec's design)."""
    qs = PurchaseItem.objects.filter(purchase__status=STATUS_RECEIVED).select_related(
        "drug", "purchase", "purchase__supplier"
    )
    if drug:
        qs = qs.filter(drug=drug)
    if supplier:
        qs = qs.filter(purchase__supplier=supplier)
    if date_from:
        qs = qs.filter(expiry_date__gte=date_from)
    if date_to:
        qs = qs.filter(expiry_date__lte=date_to)
    return qs.order_by("expiry_date")


def movement_report(*, drug=None, movement_type=None, date_from=None, date_to=None):
    """Feature Specs: 'Inventory Movement Report' — the full ledger,
    append-only per apps/stock/models.py."""
    qs = InventoryMovement.objects.select_related("drug", "user")
    if drug:
        qs = qs.filter(drug=drug)
    if movement_type:
        qs = qs.filter(movement_type=movement_type)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def stock_adjustment_report(*, adjustment_type=None, drug=None, date_from=None, date_to=None):
    """Feature Specs: 'Stock Adjustment Report'."""
    qs = StockAdjustment.objects.select_related("drug", "recorded_by")
    if adjustment_type:
        qs = qs.filter(adjustment_type=adjustment_type)
    if drug:
        qs = qs.filter(drug=drug)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs
