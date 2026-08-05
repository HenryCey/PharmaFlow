"""
Hand-written to match model state exactly. Verified field-by-field
against apps/purchases/models.py, including the custom Meta.permissions
(same drift class fixed twice already this project — checked carefully
here to avoid a third occurrence).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


PURCHASE_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("ordered", "Ordered"),
    ("received", "Received"),
    ("cancelled", "Cancelled"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("inventory", "0001_initial"),
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("purchase_number", models.CharField(editable=False, max_length=30, unique=True)),
                ("purchase_date", models.DateField()),
                ("expected_delivery", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=PURCHASE_STATUS_CHOICES, default="draft", max_length=15)),
                ("notes", models.TextField(blank=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("tax", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("grand_total", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("received_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("supplier", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders", to="suppliers.supplier",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders_created",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("received_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="purchase_orders_received", to=settings.AUTH_USER_MODEL,
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="purchase_orders_cancelled", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("receive_purchaseorder", "Can receive a purchase order"),
                    ("cancel_purchaseorder", "Can cancel a purchase order"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PurchaseItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=12)),
                ("selling_price", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    help_text="Intended resale price for this batch — applied to the Drug catalog on receiving.",
                )),
                ("batch_number", models.CharField(blank=True, max_length=50)),
                ("manufacturing_date", models.DateField(blank=True, null=True)),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("purchase", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="items", to="purchases.purchaseorder",
                )),
                ("drug", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="purchase_items", to="inventory.drug",
                )),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
