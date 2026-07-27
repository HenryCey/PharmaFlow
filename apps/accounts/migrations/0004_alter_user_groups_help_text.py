"""
Bug fix (v1.0.3): brings migration state in line with the model's actual
current state — no model change was made here.

User.groups is inherited unmodified from django.contrib.auth.models.
PermissionsMixin, whose real help_text is the two-sentence version below.
The hand-written 0001_initial.py migration truncated it to the first
sentence only, so `makemigrations` correctly detected a pending change
between the model's true state and the recorded migration state ever
since the project was created. Fixing the migration, not the model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0003_loginhistory_user_on_delete_set_null"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "The groups this user belongs to. A user will get all permissions "
                    "granted to each of their groups."
                ),
                related_name="user_set",
                related_query_name="user",
                to="auth.group",
                verbose_name="groups",
            ),
        ),
    ]
