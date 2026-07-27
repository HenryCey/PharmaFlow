import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion

import apps.accounts.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("group", models.OneToOneField(
                    editable=False, on_delete=django.db.models.deletion.CASCADE,
                    related_name="role", to="auth.group",
                )),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(
                    default=False,
                    help_text="Designates that this user has all permissions without explicitly assigning them.",
                    verbose_name="superuser status",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("username", models.CharField(max_length=150, unique=True)),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("inactive", "Inactive")],
                    default="active", max_length=10,
                )),
                ("is_staff", models.BooleanField(default=False)),
                ("groups", models.ManyToManyField(
                    blank=True,
                    help_text="The groups this user belongs to.",
                    related_name="user_set", related_query_name="user",
                    to="auth.group", verbose_name="groups",
                )),
                ("role", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="users", to="accounts.role",
                )),
                ("user_permissions", models.ManyToManyField(
                    blank=True,
                    help_text="Specific permissions for this user.",
                    related_name="user_set", related_query_name="user",
                    to="auth.permission", verbose_name="user permissions",
                )),
            ],
            options={
                "ordering": ["username"],
                "permissions": [
                    ("manage_users", "Can create, edit and deactivate users"),
                    ("manage_roles", "Can create and edit roles and permissions"),
                ],
            },
            managers=[
                ("objects", apps.accounts.managers.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="LoginHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username_attempted", models.CharField(max_length=150)),
                ("success", models.BooleanField()),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="login_history", to="accounts.user",
                )),
            ],
            options={
                "ordering": ["-timestamp"],
                "verbose_name_plural": "Login history",
            },
        ),
    ]
