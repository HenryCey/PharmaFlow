"""
Hand-written to match model state exactly (see CHANGELOG for why this
sandbox can't run `makemigrations` directly). Verified field-by-field
against apps/stock/models.py.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


MOVEMENT_TYPE_CHOICES = [
    ("sale", "Sale"),
    ("sale_cancellation", "Sale Cancellation"),
    ("adjustment", "Adjustment"),
]
ADJUSTMENT_TYPE_CHOICES = [
    ("opening_stock", "Opening Stock"),
    ("damage", "Damage"),
    ("expired", "Expired Drugs"),
    ("lost", "Lost Items"),
    ("correction", "Correction"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("movement_type", models.CharField(choices=MOVEMENT_TYPE_CHOICES, max_length=20)),
                ("quantity", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    help_text="Signed: positive increases stock, negative decreases it.",
                )),
                ("reference", models.CharField(
                    blank=True, max_length=50,
                    help_text="e.g. a Sale's receipt number, or 'ADJ-<id>'.",
                )),
                ("remarks", models.CharField(blank=True, max_length=255)),
                ("drug", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="inventory.drug",
                )),
                ("user", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="stock_movements", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["drug", "created_at"], name="stock_invmv_drug_created_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="StockAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantity", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    help_text="Signed: positive adds stock (e.g. Opening Stock), negative removes it (e.g. Damage).",
                )),
                ("adjustment_type", models.CharField(choices=ADJUSTMENT_TYPE_CHOICES, max_length=20)),
                ("reason", models.TextField(help_text="Required — Blueprint: 'Stock adjustments require a reason.'")),
                ("drug", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="adjustments", to="inventory.drug",
                )),
                ("recorded_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="stock_adjustments", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
