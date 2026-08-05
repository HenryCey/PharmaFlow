"""
Purchase Orders — Sprint 4. Completes the inventory lifecycle Sprint 3
left half-finished: Sales/Adjustments could only ever take stock out or
correct it; nothing could bring it in except manually-typed Opening
Stock. Purchases is the third and final writer into the InventoryMovement
ledger introduced in Sprint 3 (see apps/stock).

Status lifecycle: Draft -> Ordered -> Received, with Cancel available
from Draft or Ordered. Only Draft orders can have their items edited.
Receiving is the one action that touches the stock ledger — creating or
editing a Draft/Ordered order never does.
"""
from django.db import models

from apps.common.models import TimeStampedModel


STATUS_DRAFT = "draft"
STATUS_ORDERED = "ordered"
STATUS_RECEIVED = "received"
STATUS_CANCELLED = "cancelled"
PURCHASE_STATUS_CHOICES = [
    (STATUS_DRAFT, "Draft"),
    (STATUS_ORDERED, "Ordered"),
    (STATUS_RECEIVED, "Received"),
    (STATUS_CANCELLED, "Cancelled"),
]


class PurchaseOrder(TimeStampedModel):
    purchase_number = models.CharField(max_length=30, unique=True, editable=False)
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_orders",
    )
    purchase_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=PURCHASE_STATUS_CHOICES, default=STATUS_DRAFT)
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="purchase_orders_created",
    )
    received_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="purchase_orders_received",
        null=True, blank=True,
    )
    received_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="purchase_orders_cancelled",
        null=True, blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("receive_purchaseorder", "Can receive a purchase order"),
            ("cancel_purchaseorder", "Can cancel a purchase order"),
        ]

    def __str__(self):
        return self.purchase_number

    @property
    def is_editable(self):
        return self.status == STATUS_DRAFT


class PurchaseItem(TimeStampedModel):
    purchase = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    drug = models.ForeignKey(
        "inventory.Drug", on_delete=models.PROTECT, related_name="purchase_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Intended resale price for this batch — applied to the Drug catalog on receiving.",
    )
    batch_number = models.CharField(max_length=50, blank=True)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.drug.name} ({self.purchase.purchase_number})"
