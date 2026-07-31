"""
Hand-written to match model state exactly. Verified field-by-field
against apps/customers/models.py.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=150)),
                ("phone", models.CharField(max_length=20, unique=True)),
                ("address", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
