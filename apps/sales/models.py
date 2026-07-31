"""
sales models — Database Spec's "Sales" and "Sale Items" entities.

SaleItem.unit_price is deliberately a snapshot copied from Drug.selling_price
at the moment of sale, never re-read from the catalog later — a drug's
price changing next month must not silently change what a receipt from
today says it cost. Sale.total is likewise a stored, computed-once value,
not a property — Database Spec lists it as a stored field, and a stored
total is also what a receipt must reprint identically on every future view.
"""
from django.db import models

from apps.common.models import TimeStampedModel


PAYMENT_CASH = "cash"
PAYMENT_CARD = "card"
PAYMENT_TRANSFER = "transfer"
PAYMENT_MOBILE_MONEY = "mobile_money"
PAYMENT_METHOD_CHOICES = [
    (PAYMENT_CASH, "Cash"),
    (PAYMENT_CARD, "Card"),
    (PAYMENT_TRANSFER, "Bank Transfer"),
    (PAYMENT_MOBILE_MONEY, "Mobile Money"),
]

STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
SALE_STATUS_CHOICES = [
    (STATUS_COMPLETED, "Completed"),
    (STATUS_CANCELLED, "Cancelled"),
]


class Sale(TimeStampedModel):
    """
    Not soft-deletable — a Sale is never deleted at all, cancelled or not
    (Feature Specs: "Sale Cancellation History" is itself an audit
    requirement). `status` is the only lifecycle field; the row is
    permanent either way.
    """

    receipt_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="sales",
        null=True, blank=True, help_text="Blank = walk-in customer.",
    )
    cashier = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="sales_made",
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=SALE_STATUS_CHOICES, default=STATUS_COMPLETED)

    cancelled_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="sales_cancelled",
        null=True, blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("cancel_sale", "Can cancel a completed sale"),
            ("view_all_sales", "Can view all cashiers' sales, not just their own"),
        ]

    def __str__(self):
        return self.receipt_number


class SaleItem(TimeStampedModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    drug = models.ForeignKey(
        "inventory.Drug", on_delete=models.PROTECT, related_name="sale_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Snapshot of Drug.selling_price at the moment of sale.",
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.drug.name} ({self.sale.receipt_number})"

    @property
    def line_total(self):
        return (self.quantity * self.unit_price) - self.discount
