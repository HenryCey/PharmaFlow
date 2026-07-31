"""
stock business logic.

record_movement() is the ONLY function anywhere in the project permitted
to write Drug.current_stock. Sales (checkout_service, sales_service) and
Stock Adjustments both call this — never touch current_stock directly.
This is what makes the Technical Architecture's "ledger-first inventory"
rule an enforced invariant rather than a convention someone can forget.
"""
from django.db import transaction

from apps.inventory.models import Drug

from .models import InventoryMovement, StockAdjustment, MOVEMENT_ADJUSTMENT


class InsufficientStockError(Exception):
    """Raised when a movement would take a drug's stock below zero."""

    def __init__(self, drug, requested, available):
        self.drug = drug
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {drug.name}: requested {requested}, only {available} available."
        )


@transaction.atomic
def record_movement(*, drug, movement_type, quantity, user=None, reference="", remarks=""):
    """
    Locks the Drug row, applies a signed quantity change, writes the
    InventoryMovement audit row, and updates Drug.current_stock — all in
    one transaction. Never allows stock to go negative.
    """
    locked_drug = Drug.objects.select_for_update().get(pk=drug.pk)
    new_stock = locked_drug.current_stock + quantity

    if new_stock < 0:
        raise InsufficientStockError(
            locked_drug, requested=abs(quantity), available=locked_drug.current_stock
        )

    InventoryMovement.objects.create(
        drug=locked_drug,
        movement_type=movement_type,
        quantity=quantity,
        user=user,
        reference=reference,
        remarks=remarks,
    )
    locked_drug.current_stock = new_stock
    locked_drug.save(update_fields=["current_stock"])
    return locked_drug


@transaction.atomic
def create_adjustment(*, drug, quantity, adjustment_type, reason, user):
    """Creates the audit-facing StockAdjustment row and writes the
    matching ledger movement in the same transaction."""
    adjustment = StockAdjustment.objects.create(
        drug=drug, quantity=quantity, adjustment_type=adjustment_type,
        reason=reason, recorded_by=user,
    )
    record_movement(
        drug=drug, movement_type=MOVEMENT_ADJUSTMENT, quantity=quantity,
        user=user, reference=f"ADJ-{adjustment.pk}", remarks=reason,
    )
    return adjustment
