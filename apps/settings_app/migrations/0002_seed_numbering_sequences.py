"""Seeds the three document numbering sequences with sensible default
prefixes, so Sales/Purchases/Documents modules have a working sequence
the moment they're built in later sprints."""
from django.db import migrations

DEFAULTS = [
    ("sale_receipt", "RCT-"),
    ("invoice", "INV-"),
    ("purchase_order", "PO-"),
]


def seed(apps, schema_editor):
    NumberingSequence = apps.get_model("settings_app", "NumberingSequence")
    for document_type, prefix in DEFAULTS:
        NumberingSequence.objects.get_or_create(
            document_type=document_type, defaults={"prefix": prefix}
        )


def unseed(apps, schema_editor):
    NumberingSequence = apps.get_model("settings_app", "NumberingSequence")
    NumberingSequence.objects.filter(document_type__in=[d for d, _ in DEFAULTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
