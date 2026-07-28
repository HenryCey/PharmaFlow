"""
inventory business logic.

Kept minimal in Sprint 2 — most "real" business logic (stock writes,
reorder triggers) belongs to the future `stock`/`notifications` apps.
What lives here is genuinely cross-cutting query logic for the catalog
itself, so it isn't duplicated between the list view and any future
report/API use of the same filter.
"""
from django.db.models import F


def low_stock_drugs(queryset):
    """Drugs at or below their reorder level (Feature Specs: Low Stock
    Alerts / Inventory Monitoring). Used by the Drug list's "Low Stock"
    filter — kept here so the same rule can be reused by the
    Notifications module in a later sprint without duplicating it."""
    return queryset.filter(current_stock__lte=F("reorder_level"))
