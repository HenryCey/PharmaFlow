"""
Database Spec's "Customers" entity: Name, Phone, Address. Walk-in
customers are intentionally NOT a database row — Sale.customer is
nullable, satisfying the Feature Spec's "Walk-in Customers" requirement
without a placeholder record to maintain.

Inherits SoftDeleteModel — apps/common/models.py's own docstring already
names "Customers" as one of the models meant to use it, so a deleted
customer's Sales history stays intact.
"""
from django.db import models

from apps.common.models import TimeStampedModel, SoftDeleteModel


class Customer(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
