"""
Cart is server-side, session-scoped state — not client-only Alpine state
— so stock can be validated server-side before checkout, and so a
cashier's in-progress cart survives a page reload. Each function takes
`session` directly (not `request`) to keep this testable without a full
request/response cycle.

Session storage note: Django's session serializer is JSON, which can't
store Decimal, so quantities are stored as strings and converted to
Decimal on read.
"""
from decimal import Decimal

from apps.inventory.models import Drug

CART_SESSION_KEY = "pos_cart"


def _get_raw_cart(session):
    return session.setdefault(CART_SESSION_KEY, {})


def add_item(session, drug_id, quantity=1):
    cart = _get_raw_cart(session)
    drug_id = str(drug_id)
    current = Decimal(cart.get(drug_id, "0"))
    cart[drug_id] = str(current + Decimal(quantity))
    session.modified = True


def set_item_quantity(session, drug_id, quantity):
    cart = _get_raw_cart(session)
    drug_id = str(drug_id)
    quantity = Decimal(quantity)
    if quantity <= 0:
        cart.pop(drug_id, None)
    else:
        cart[drug_id] = str(quantity)
    session.modified = True


def remove_item(session, drug_id):
    cart = _get_raw_cart(session)
    cart.pop(str(drug_id), None)
    session.modified = True


def clear(session):
    session[CART_SESSION_KEY] = {}
    session.modified = True


def is_empty(session):
    return len(_get_raw_cart(session)) == 0


def get_cart_lines(session):
    """
    Returns cart lines with each drug's *current* selling price — prices
    aren't frozen until checkout actually creates the Sale/SaleItem rows,
    so a cart left open across a price change reflects the new price
    (matches how a physical POS terminal would behave, not a "reserved
    quote"). A single filter() query avoids N+1 lookups.
    """
    raw_cart = _get_raw_cart(session)
    if not raw_cart:
        return []
    drugs = {str(d.pk): d for d in Drug.objects.filter(pk__in=raw_cart.keys())}
    lines = []
    for drug_id, quantity in raw_cart.items():
        drug = drugs.get(drug_id)
        if drug is None:
            continue  # drug was discontinued/deleted after being added to cart
        quantity = Decimal(quantity)
        unit_price = drug.selling_price
        lines.append({
            "drug": drug,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": (quantity * unit_price),
        })
    return lines


def get_cart_subtotal(session):
    return sum((line["line_total"] for line in get_cart_lines(session)), Decimal("0"))
