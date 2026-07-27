"""
settings_app business logic.

Numbering generation is business logic (must be atomic, must never repeat
or skip in a way that breaks receipts/invoices), so it lives here rather
than inline in a view — per the approved architecture, services.py exists
only where real business logic lives.
"""
from django.db import transaction

from .models import NumberingSequence


@transaction.atomic
def generate_document_number(document_type: str) -> str:
    """
    Atomically reserves and returns the next formatted number for a given
    document type (e.g. "INV-00001"). Locks the row for the duration of
    the transaction so two simultaneous sales can never receive the same
    receipt number.
    """
    sequence = (
        NumberingSequence.objects.select_for_update()
        .get(document_type=document_type)
    )
    formatted = f"{sequence.prefix}{str(sequence.next_number).zfill(sequence.padding)}"
    sequence.next_number += 1
    sequence.save(update_fields=["next_number"])
    return formatted
