"""
Everything about an *existing* Sale that isn't checkout itself: viewing
history (with row-level scoping), cancelling one, and the lightweight
daily summary. Kept separate from checkout_service since checkout is a
single atomic write path, while this module is several independent
read/mutate operations against sales that already exist.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.stock.services import record_movement
from apps.stock.models import MOVEMENT_SALE_CANCELLATION

from .models import Sale, SaleItem, STATUS_COMPLETED, STATUS_CANCELLED


class SaleAlreadyCancelledError(Exception):
    pass


def get_sales_queryset(user):
    """
    Row-level scoping per the Sprint 3 Permissions Matrix: a Cashier sees
    only their own sales; anyone with `sales.view_all_sales`
    (Owner/Administrator/Pharmacist) sees everyone's.
    """
    qs = Sale.objects.select_related("customer", "cashier")
    if user.has_perm("sales.view_all_sales"):
        return qs
    return qs.filter(cashier=user)


@transaction.atomic
def cancel_sale(*, sale, user, reason):
    """
    Reverses stock for every line via a new (positive) ledger movement —
    the original `sale` movements are never edited or deleted, since the
    ledger is append-only. `Sale.status` becomes the only record of the
    cancellation on the Sale itself; the InventoryMovement rows are the
    audit trail for the stock side of it.
    """
    if sale.status == STATUS_CANCELLED:
        raise SaleAlreadyCancelledError(f"{sale.receipt_number} is already cancelled.")

    for item in sale.items.select_related("drug"):
        record_movement(
            drug=item.drug,
            movement_type=MOVEMENT_SALE_CANCELLATION,
            quantity=item.quantity,
            user=user,
            reference=sale.receipt_number,
            remarks=reason,
        )

    sale.status = STATUS_CANCELLED
    sale.cancelled_by = user
    sale.cancelled_at = timezone.now()
    sale.cancellation_reason = reason
    sale.save(update_fields=["status", "cancelled_by", "cancelled_at", "cancellation_reason"])
    return sale


def daily_sales_summary(*, date=None, cashier=None):
    """
    Deliberately lightweight — "today's totals", not the full Reports
    engine (date ranges, PDF export, Profit/Inventory/Expiry reports)
    that Sprint 4 owns per the Feature Specs. See the Sprint 3
    Implementation Plan for why this is scoped down.
    """
    date = date or timezone.localdate()
    qs = Sale.objects.filter(created_at__date=date, status=STATUS_COMPLETED)
    if cashier is not None:
        qs = qs.filter(cashier=cashier)

    totals = qs.aggregate(revenue=Sum("total"))
    top_drugs = (
        SaleItem.objects.filter(sale__in=qs)
        .values("drug__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )

    return {
        "date": date,
        "sale_count": qs.count(),
        "revenue": totals["revenue"] or Decimal("0"),
        "top_drugs": list(top_drugs),
    }
