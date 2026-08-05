"""
Hand-written to match model state exactly. Verified field-by-field
against apps/suppliers/models.py.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("supplier_code", models.CharField(editable=False, max_length=30, unique=True)),
                ("company_name", models.CharField(max_length=200)),
                ("contact_person", models.CharField(blank=True, max_length=150)),
                ("phone", models.CharField(max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="active", max_length=10)),
                ("notes", models.TextField(blank=True)),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="suppliers_created", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["company_name"],
            },
        ),
    ]
