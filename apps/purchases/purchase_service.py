"""
Everything about a PurchaseOrder's own lifecycle that ISN'T receiving —
creating/editing a Draft, placing an order, and cancelling. None of this
ever touches the stock ledger; only receiving_service.receive_purchase()
does that, which is why it's a separate module.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.settings_app.services import generate_document_number

from .models import PurchaseOrder, PurchaseItem, STATUS_DRAFT, STATUS_ORDERED, STATUS_CANCELLED


class PurchaseOrderNotEditableError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


def _sync_items(order, items):
    """Replaces an order's items wholesale and recomputes totals. Simpler
    and less error-prone than diffing individual line edits, and safe
    because this is only ever called on a Draft order (see callers)."""
    order.items.all().delete()
    subtotal = Decimal("0")
    for item in items:
        line_subtotal = item["quantity"] * item["unit_cost"]
        subtotal += line_subtotal
        PurchaseItem.objects.create(purchase=order, subtotal=line_subtotal, **item)
    order.subtotal = subtotal
    order.grand_total = subtotal + order.tax - order.discount
    order.save(update_fields=["subtotal", "grand_total"])


@transaction.atomic
def create_purchase_order(*, supplier, purchase_date, expected_delivery, notes,
                           tax, discount, created_by, items):
    purchase_number = generate_document_number("purchase_order")
    order = PurchaseOrder.objects.create(
        purchase_number=purchase_number, supplier=supplier, purchase_date=purchase_date,
        expected_delivery=expected_delivery, notes=notes, tax=tax, discount=discount,
        created_by=created_by,
    )
    _sync_items(order, items)
    return order


@transaction.atomic
def update_purchase_order(*, order, purchase_date, expected_delivery, notes, tax, discount, items):
    if not order.is_editable:
        raise PurchaseOrderNotEditableError(
            f"{order.purchase_number} is {order.get_status_display()} and can no longer be edited."
        )
    order.purchase_date = purchase_date
    order.expected_delivery = expected_delivery
    order.notes = notes
    order.tax = tax
    order.discount = discount
    order.save(update_fields=["purchase_date", "expected_delivery", "notes", "tax", "discount"])
    _sync_items(order, items)
    return order


def place_order(*, order):
    """Draft -> Ordered. Locks items from further editing (per Meta:
    is_editable is Draft-only) — signals the PO has actually been sent
    to the supplier, distinct from still being composed internally."""
    if order.status != STATUS_DRAFT:
        raise InvalidStatusTransitionError(f"{order.purchase_number} is not a Draft.")
    order.status = STATUS_ORDERED
    order.save(update_fields=["status"])
    return order


def cancel_purchase_order(*, order, user, reason):
    if order.status not in (STATUS_DRAFT, STATUS_ORDERED):
        raise InvalidStatusTransitionError(
            f"{order.purchase_number} is {order.get_status_display()} and cannot be cancelled."
        )
    order.status = STATUS_CANCELLED
    order.cancelled_by = user
    order.cancelled_at = timezone.now()
    order.cancellation_reason = reason
    order.save(update_fields=["status", "cancelled_by", "cancelled_at", "cancellation_reason"])
    return order
