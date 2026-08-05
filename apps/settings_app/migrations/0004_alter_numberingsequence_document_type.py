from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings_app", "0003_alter_pharmacysettings_currency_symbol_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="numberingsequence",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("sale_receipt", "Sale Receipt"),
                    ("invoice", "Invoice"),
                    ("purchase_order", "Purchase Order"),
                    ("supplier_code", "Supplier Code"),
                ],
                max_length=30,
                unique=True,
            ),
        ),
    ]
