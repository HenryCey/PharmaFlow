"""
Hand-written to match model state exactly (this sandbox has no network
access to run `django-admin makemigrations` directly — see CHANGELOG for
the same caveat applied to Sprint 1). Verified field-by-field against
apps/inventory/models.py.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]
DRUG_STATUS_CHOICES = STATUS_CHOICES + [("discontinued", "Discontinued")]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="active", max_length=10)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name_plural": "Categories",
            },
        ),
        migrations.CreateModel(
            name="Manufacturer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="active", max_length=10)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DosageForm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="active", max_length=10)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Unit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="active", max_length=10)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Drug",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=200, verbose_name="Drug Name")),
                ("generic_name", models.CharField(blank=True, max_length=200)),
                ("brand_name", models.CharField(blank=True, max_length=200)),
                ("sku", models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ("barcode", models.CharField(
                    blank=True, max_length=64, null=True, unique=True,
                    help_text="Type manually or scan with a USB barcode scanner (acts as a keyboard).",
                )),
                ("strength", models.CharField(blank=True, help_text="e.g. 500mg, 250mg/5ml", max_length=50)),
                ("description", models.TextField(blank=True)),
                ("cost_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("selling_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("current_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("minimum_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("reorder_level", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=DRUG_STATUS_CHOICES, default="active", max_length=15)),
                ("category", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="drugs", to="inventory.category",
                )),
                ("manufacturer", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="drugs", to="inventory.manufacturer",
                )),
                ("dosage_form", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="drugs", to="inventory.dosageform",
                )),
                ("unit", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="drugs", to="inventory.unit",
                )),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="drugs_created", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
