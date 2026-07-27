"""
Bug fix (v1.0.1): LoginHistory.user previously cascaded on delete, which
would silently destroy audit history if a User row were ever hard-deleted.
Changed to SET_NULL — the field was already nullable, so no data migration
is needed, only the field's on_delete behavior.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_default_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loginhistory",
            name="user",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="login_history", to="accounts.user",
            ),
        ),
    ]
