"""
Receiving a purchase — the one action in this app that writes to the
stock ledger. "Receiving a Purchase must NOT directly edit Current
Stock. Instead: Create Inventory Movements using the Stock Ledger
introduced in Sprint 3. Exactly as Sales already deduct stock. Purchases
must increase stock through the ledger." — this module is exactly that,
mirroring apps/sales/checkout_service.py's shape.
"""
from django.db import transaction

from apps.stock.services import record_movement
from apps.stock.models import MOVEMENT_PURCHASE

from .models import PurchaseOrder, STATUS_DRAFT, STATUS_ORDERED, STATUS_RECEIVED
from .purchase_service import InvalidStatusTransitionError

from django.utils import timezone


@transaction.atomic
def receive_purchase(*, purchase, user):
    """
    Writes one Purchase-type InventoryMovement per line (positive
    quantity — the ledger, not this function, is what actually updates
    Drug.current_stock). Also applies each line's cost/selling price to
    the Drug catalog — a deliberate design decision (flagged to the
    team): the most recently received batch's price becomes the drug's
    current catalog price, since there's no per-batch/FEFO pricing at
    POS yet (that's explicitly future "expiry management" scope).
    Batch number/mfg/expiry stay on PurchaseItem only — Drug has never
    carried batch data, by the original Database Spec's design.
    """
    if purchase.status not in (STATUS_DRAFT, STATUS_ORDERED):
        raise InvalidStatusTransitionError(
            f"{purchase.purchase_number} is {purchase.get_status_display()} and cannot be received."
        )

    for item in purchase.items.select_related("drug"):
        record_movement(
            drug=item.drug,
            movement_type=MOVEMENT_PURCHASE,
            quantity=item.quantity,
            user=user,
            reference=purchase.purchase_number,
            remarks=f"Batch {item.batch_number}" if item.batch_number else "",
        )
        item.drug.cost_price = item.unit_cost
        item.drug.selling_price = item.selling_price
        item.drug.save(update_fields=["cost_price", "selling_price"])

    purchase.status = STATUS_RECEIVED
    purchase.received_by = user
    purchase.received_at = timezone.now()
    purchase.save(update_fields=["status", "received_by", "received_at"])
    return purchase
