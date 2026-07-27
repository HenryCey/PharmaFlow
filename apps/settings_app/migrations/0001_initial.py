from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PharmacySettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("pharmacy_name", models.CharField(max_length=200)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="settings/logo/")),
                ("address", models.TextField(blank=True)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("currency_symbol", models.CharField(default="\u20a6", max_length=5)),
                ("receipt_footer_note", models.CharField(blank=True, max_length=255)),
                ("default_printer_name", models.CharField(blank=True, max_length=100)),
            ],
            options={
                "verbose_name": "Pharmacy settings",
                "verbose_name_plural": "Pharmacy settings",
            },
        ),
        migrations.CreateModel(
            name="NumberingSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("document_type", models.CharField(
                    choices=[("sale_receipt", "Sale Receipt"), ("invoice", "Invoice"), ("purchase_order", "Purchase Order")],
                    max_length=30, unique=True,
                )),
                ("prefix", models.CharField(blank=True, max_length=10)),
                ("next_number", models.PositiveIntegerField(default=1)),
                ("padding", models.PositiveSmallIntegerField(default=5)),
            ],
            options={
                "verbose_name_plural": "Numbering sequences",
            },
        ),
    ]
