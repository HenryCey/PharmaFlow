"""
settings_app models — Pharmacy configuration (Database Spec: Settings entity).

PharmacySettings is a deliberate singleton: a single pharmacy location in
V1 (no multi-branch), so there is exactly one configuration row.
"""
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel
from django.conf import settings as django_settings


class PharmacySettings(TimeStampedModel):
    """Singleton row — enforced in save(), not just by convention."""

    pharmacy_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="settings/logo/", blank=True, null=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Single-currency configuration (Section 6 of the approved architecture).
    currency_symbol = models.CharField(
        max_length=5, default=django_settings.DEFAULT_CURRENCY_SYMBOL,
        help_text="Displayed before every price/amount throughout the app.",
    )

    # Printer / receipt settings — kept simple in Sprint 1; expanded once
    # the Documents module (Phase 5) is built.
    receipt_footer_note = models.CharField(max_length=255, blank=True)
    default_printer_name = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Pharmacy settings"
        verbose_name_plural = "Pharmacy settings"

    def clean(self):
        if not self.pk and PharmacySettings.objects.exists():
            raise ValidationError("Pharmacy settings already exist — edit the existing record.")

    def save(self, *args, **kwargs):
        self.full_clean(exclude=None, validate_unique=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.pharmacy_name or "Pharmacy Settings"

    @classmethod
    def load(cls):
        """Convenience accessor used by context processors/views/services."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(pharmacy_name="My Pharmacy")
        return obj


class NumberingSequence(TimeStampedModel):
    """
    One row per document type (Sale Receipt, Invoice, Purchase Order, ...).
    The *only* correct way to obtain the next number is
    NumberingSequence.get_next_number() in services.py — never read
    `next_number` directly and increment it in a view.
    """

    DOCUMENT_TYPE_CHOICES = [
        ("sale_receipt", "Sale Receipt"),
        ("invoice", "Invoice"),
        ("purchase_order", "Purchase Order"),
    ]

    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES, unique=True)
    prefix = models.CharField(max_length=10, blank=True)
    next_number = models.PositiveIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(
        default=5, help_text="Zero-padding width, e.g. 5 -> 00001",
    )

    class Meta:
        verbose_name_plural = "Numbering sequences"

    def __str__(self):
        return f"{self.get_document_type_display()} ({self.prefix}#####)"

    def preview_next(self):
        return f"{self.prefix}{str(self.next_number).zfill(self.padding)}"
