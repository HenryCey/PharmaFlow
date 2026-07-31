"""
Hand-written to match model state exactly. Verified field-by-field
against apps/sales/models.py.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("card", "Card"),
    ("transfer", "Bank Transfer"),
    ("mobile_money", "Mobile Money"),
]
SALE_STATUS_CHOICES = [
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("inventory", "0001_initial"),
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("receipt_number", models.CharField(max_length=30, unique=True)),
                ("payment_method", models.CharField(choices=PAYMENT_METHOD_CHOICES, max_length=20)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=SALE_STATUS_CHOICES, default="completed", max_length=15)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("customer", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="sales", to="customers.customer",
                    help_text="Blank = walk-in customer.",
                )),
                ("cashier", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="sales_made",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sales_cancelled", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("cancel_sale", "Can cancel a completed sale"),
                    ("view_all_sales", "Can view all cashiers' sales, not just their own"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit_price", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    help_text="Snapshot of Drug.selling_price at the moment of sale.",
                )),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sale", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="items", to="sales.sale",
                )),
                ("drug", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="sale_items", to="inventory.drug",
                )),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
