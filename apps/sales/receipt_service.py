"""
Builds the context a receipt template needs. Kept separate from
checkout_service — creating a sale and displaying/reprinting one are
different concerns (a receipt can be viewed many times after the sale
that created it is long done).
"""
from apps.settings_app.models import PharmacySettings


def get_receipt_context(sale):
    return {
        "sale": sale,
        "items": sale.items.select_related("drug", "drug__unit"),
        "pharmacy": PharmacySettings.load(),
    }
