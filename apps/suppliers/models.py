"""
Supplier Management (Sprint 4). Inherits SoftDeleteModel — Purchase
Orders will reference Supplier with PROTECT, so a supplier a pharmacy
stops using can be deactivated/soft-deleted without breaking historical
purchase records, matching the same precedent as Drug/Customer.
"""
from django.db import models

from apps.common.models import TimeStampedModel, SoftDeleteModel

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_CHOICES = [
    (STATUS_ACTIVE, "Active"),
    (STATUS_INACTIVE, "Inactive"),
]


class Supplier(TimeStampedModel, SoftDeleteModel):
    # Auto-generated via settings_app's existing NumberingSequence service
    # (document_type="supplier_code") — never user-editable.
    supplier_code = models.CharField(max_length=30, unique=True, editable=False)

    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="suppliers_created",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name
