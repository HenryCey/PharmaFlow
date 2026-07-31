"""
stock models — the inventory ledger.

Per the Technical Architecture: "inventory quantities are always derived
from stock movements and sales" (Database Spec's general rule). This app
is shared infrastructure required by Sales (and, later, Purchases) — not
a standalone business module in its own right, which is why it has no
sidebar entry or dedicated top-level UI. It's reached from within the
Drug detail page (apps/inventory) via an "Adjust Stock" action and a
Movement History section.

InventoryMovement is append-only: rows are never edited or deleted once
created, since it's the audit trail Sales cancellations and Adjustments
both write to. The one and only place permitted to write to it — or to
Drug.current_stock — is stock/services.py:record_movement().
"""
from django.db import models

from apps.common.models import TimeStampedModel


MOVEMENT_SALE = "sale"
MOVEMENT_SALE_CANCELLATION = "sale_cancellation"
MOVEMENT_ADJUSTMENT = "adjustment"
MOVEMENT_TYPE_CHOICES = [
    (MOVEMENT_SALE, "Sale"),
    (MOVEMENT_SALE_CANCELLATION, "Sale Cancellation"),
    (MOVEMENT_ADJUSTMENT, "Adjustment"),
    # "purchase" is intentionally not listed yet — added when the
    # Purchases module ships and becomes the third writer into this ledger.
]

ADJUSTMENT_OPENING_STOCK = "opening_stock"
ADJUSTMENT_DAMAGE = "damage"
ADJUSTMENT_EXPIRED = "expired"
ADJUSTMENT_LOST = "lost"
ADJUSTMENT_CORRECTION = "correction"
ADJUSTMENT_TYPE_CHOICES = [
    (ADJUSTMENT_OPENING_STOCK, "Opening Stock"),
    (ADJUSTMENT_DAMAGE, "Damage"),
    (ADJUSTMENT_EXPIRED, "Expired Drugs"),
    (ADJUSTMENT_LOST, "Lost Items"),
    (ADJUSTMENT_CORRECTION, "Correction"),
]


class InventoryMovement(TimeStampedModel):
    drug = models.ForeignKey(
        "inventory.Drug", on_delete=models.PROTECT, related_name="movements",
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Signed: positive increases stock, negative decreases it.",
    )
    reference = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. a Sale's receipt number, or 'ADJ-<id>'.",
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="stock_movements",
        null=True, blank=True,
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["drug", "created_at"], name="stock_invmv_drug_created_idx"),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity:+} — {self.drug.name}"


class StockAdjustment(TimeStampedModel):
    """
    Database Spec's "Stock Adjustments" entity. Also the mechanism used to
    seed opening stock for a drug, since Purchases/Suppliers (the other
    normal way stock enters the system) are out of scope until a later
    sprint — see the Sprint 3 Implementation Plan's flagged dependency.
    """

    drug = models.ForeignKey(
        "inventory.Drug", on_delete=models.PROTECT, related_name="adjustments",
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Signed: positive adds stock (e.g. Opening Stock), negative removes it (e.g. Damage).",
    )
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    reason = models.TextField(help_text="Required — Blueprint: 'Stock adjustments require a reason.'")
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="stock_adjustments",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_adjustment_type_display()} {self.quantity:+} — {self.drug.name}"
