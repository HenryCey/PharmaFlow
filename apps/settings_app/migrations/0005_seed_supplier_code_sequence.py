"""Seeds the supplier_code numbering sequence for Sprint 4 (Supplier
Management) — same pattern as 0002_seed_numbering_sequences.py, added as
a new migration rather than editing that one, per project policy."""
from django.db import migrations

DOCUMENT_TYPE = "supplier_code"
PREFIX = "SUP-"


def seed(apps, schema_editor):
    NumberingSequence = apps.get_model("settings_app", "NumberingSequence")
    NumberingSequence.objects.get_or_create(
        document_type=DOCUMENT_TYPE, defaults={"prefix": PREFIX}
    )


def unseed(apps, schema_editor):
    NumberingSequence = apps.get_model("settings_app", "NumberingSequence")
    NumberingSequence.objects.filter(document_type=DOCUMENT_TYPE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings_app", "0004_alter_numberingsequence_document_type"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
