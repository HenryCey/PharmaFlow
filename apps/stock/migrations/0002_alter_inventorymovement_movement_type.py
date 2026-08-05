from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventorymovement",
            name="movement_type",
            field=models.CharField(
                choices=[
                    ("sale", "Sale"),
                    ("sale_cancellation", "Sale Cancellation"),
                    ("adjustment", "Adjustment"),
                    ("purchase", "Purchase"),
                ],
                max_length=20,
            ),
        ),
    ]
