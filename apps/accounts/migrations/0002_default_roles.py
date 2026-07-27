"""
Creates the four default Roles (Owner, Administrator, Pharmacist, Cashier)
required by the Blueprint, each backed by its own auth.Group.

This migration only creates the Role/Group rows — it does NOT assign
permissions. Django creates each app's add/change/delete/view Permission
rows via the post_migrate signal, which fires only after the *entire*
`migrate` run finishes, so a data migration running mid-`migrate` cannot
reliably see permissions for apps migrated after it. Permission
assignment is handled by the `seed_role_permissions` management command
(apps/accounts/management/commands/seed_role_permissions.py), run once
after every `migrate`.
"""
from django.db import migrations


ROLE_DEFINITIONS = [
    ("Owner", "Full access to every module and setting."),
    ("Administrator", "Manages users, roles and pharmacy configuration."),
    ("Pharmacist", "Handles inventory, sales and drug-related workflows."),
    ("Cashier", "Handles point-of-sale transactions only."),
]


def create_default_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Group = apps.get_model("auth", "Group")

    for name, description in ROLE_DEFINITIONS:
        group, _ = Group.objects.get_or_create(name=name)
        role, created = Role.objects.get_or_create(
            name=name, defaults={"description": description, "group": group}
        )
        if role.group_id != group.id:
            role.group_id = group.id
            role.save(update_fields=["group"])


def remove_default_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name__in=[n for n, _ in ROLE_DEFINITIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_roles, remove_default_roles),
    ]
