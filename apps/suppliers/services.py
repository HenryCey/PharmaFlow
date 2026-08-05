"""
Kept minimal — Supplier is mostly plain CRUD. The one piece of real
business logic is generating supplier_code before the row exists, which
belongs here rather than in the view, matching how checkout_service
generates a Sale's receipt_number before creating the Sale.
"""
from django.db import transaction

from apps.settings_app.services import generate_document_number

from .models import Supplier


@transaction.atomic
def create_supplier(*, created_by, **fields):
    supplier_code = generate_document_number("supplier_code")
    return Supplier.objects.create(supplier_code=supplier_code, created_by=created_by, **fields)
