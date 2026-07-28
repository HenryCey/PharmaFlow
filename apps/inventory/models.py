"""
inventory models — Drug Categories, Manufacturers, Dosage Forms, Units,
and Drugs (Sprint 2 scope: Database Spec's "Drug Categories" and "Drugs"
entities, plus Manufacturer/Dosage Form/Unit lookup tables added per the
Sprint 2 Build Request).

Per the Technical Architecture, this app owns the catalog only — "what a
drug *is*" — never quantity writes. `stock` (a later sprint) owns the
ledger ("what happened to its quantity"). See Drug.current_stock below
for how that boundary is enforced in this sprint.
"""
from django.db import models

from apps.common.models import TimeStampedModel, SoftDeleteModel


STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_CHOICES = [
    (STATUS_ACTIVE, "Active"),
    (STATUS_INACTIVE, "Inactive"),
]


class Category(TimeStampedModel):
    """Drug Categories (Database Spec). Simple lookup table — deleted the
    same way Role is (hard delete), since it carries no history of its
    own; Drug references it with PROTECT so an in-use category can't be
    removed until it's reassigned."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Manufacturer(TimeStampedModel):
    """Not present in the original Database Spec — added per the Sprint 2
    Build Request's explicit "Manufacturers" module. Additive only; does
    not conflict with any documented entity."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DosageForm(TimeStampedModel):
    """Tablet, Capsule, Syrup, Injection, Cream, Suspension, Drops, etc."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    """Tablet, Bottle, Carton, Pack, Strip, Tube, Piece, etc."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Drug(TimeStampedModel, SoftDeleteModel):
    """
    Drug Products (Database Spec: "Drugs"). Inherits SoftDeleteModel —
    per apps/common/models.py, this is reserved for history-bearing
    records (Users, Drugs, Customers, Suppliers), since later sprints
    (Sales, Purchases) will reference Drug rows that must never disappear
    from historical documents even after being discontinued.

    NOTE ON current_stock (flagged conflict, see chat): the Technical
    Architecture requires stock quantity to be written only inside the
    same transaction as an InventoryMovement (from Purchase, Sale, or
    Stock Adjustment) — never edited directly elsewhere. Those modules
    are out of scope for Sprint 2. current_stock therefore exists as a
    real field (Database Spec requires it) but is deliberately excluded
    from DrugForm and rendered read-only everywhere in this sprint's UI.
    It will become writable once the `stock` app exists to own it.
    """

    STATUS_DISCONTINUED = "discontinued"
    DRUG_STATUS_CHOICES = STATUS_CHOICES + [
        (STATUS_DISCONTINUED, "Discontinued"),
    ]

    name = models.CharField("Drug Name", max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    brand_name = models.CharField(max_length=200, blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    barcode = models.CharField(
        max_length=64, unique=True, blank=True, null=True,
        help_text="Type manually or scan with a USB barcode scanner (acts as a keyboard).",
    )

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="drugs")
    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.PROTECT, related_name="drugs", null=True, blank=True
    )
    dosage_form = models.ForeignKey(
        DosageForm, on_delete=models.PROTECT, related_name="drugs", null=True, blank=True
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="drugs")

    strength = models.CharField(max_length=50, blank=True, help_text="e.g. 500mg, 250mg/5ml")
    description = models.TextField(blank=True)

    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # See class docstring — read-only in Sprint 2, owned by the future
    # `stock` app once Purchases/Stock Adjustments exist.
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=15, choices=DRUG_STATUS_CHOICES, default=STATUS_ACTIVE)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="drugs_created",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0
