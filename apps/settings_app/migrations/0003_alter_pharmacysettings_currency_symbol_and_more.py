"""
Bug fix (v1.0.3): brings migration state in line with the model's actual
current state — no model change was made here.

Both PharmacySettings.currency_symbol and NumberingSequence.padding have
carried a help_text in models.py since Sprint 1, but the hand-written
0001_initial.py migration for this app omitted it on both fields, so
`makemigrations` correctly detected a pending change ever since the
project was created. Fixing the migration, not the model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings_app", "0002_seed_numbering_sequences"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pharmacysettings",
            name="currency_symbol",
            field=models.CharField(
                default="\u20a6",
                help_text="Displayed before every price/amount throughout the app.",
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name="numberingsequence",
            name="padding",
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="Zero-padding width, e.g. 5 -> 00001",
            ),
        ),
    ]
