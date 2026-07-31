"""
Checkout: turns the session cart into a real, permanent Sale + SaleItem
set, deducting stock atomically. This is the one place a cart's contents
become financially and legally real — everything before this point (the
cart itself) is disposable session state.
"""
from decimal import Decimal

from django.db import transaction

from apps.settings_app.services import generate_document_number
from apps.stock.services import record_movement, InsufficientStockError
from apps.stock.models import MOVEMENT_SALE

from . import cart_service
from .models import Sale, SaleItem


class EmptyCartError(Exception):
    """Raised if checkout is attempted with nothing in the cart."""


@transaction.atomic
def complete_sale(*, session, cashier, customer=None, payment_method, discount=Decimal("0")):
    """
    Validates and deducts stock for every cart line, creates the Sale and
    its SaleItems, and clears the cart — all in one transaction. If any
    line has insufficient stock, the whole sale is rolled back (including
    any lines already deducted earlier in the loop) and the cart is left
    untouched so the cashier can adjust quantities and retry.
    """
    lines = cart_service.get_cart_lines(session)
    if not lines:
        raise EmptyCartError("Cannot check out an empty cart.")

    subtotal = sum((line["line_total"] for line in lines), Decimal("0"))
    total = subtotal - discount

    receipt_number = generate_document_number("sale_receipt")

    sale = Sale.objects.create(
        receipt_number=receipt_number,
        customer=customer,
        cashier=cashier,
        payment_method=payment_method,
        discount=discount,
        total=total,
    )

    for line in lines:
        SaleItem.objects.create(
            sale=sale,
            drug=line["drug"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
        )
        # Raises InsufficientStockError (uncaught here) if this line can't
        # be fulfilled — the @transaction.atomic above rolls back the
        # whole sale, including any SaleItems/movements already written
        # earlier in this same loop.
        record_movement(
            drug=line["drug"],
            movement_type=MOVEMENT_SALE,
            quantity=-line["quantity"],
            user=cashier,
            reference=receipt_number,
        )

    cart_service.clear(session)
    return sale
