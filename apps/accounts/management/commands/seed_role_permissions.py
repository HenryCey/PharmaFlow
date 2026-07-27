"""
Assigns baseline permissions to the four default Roles.

Run this once after `migrate` (and again after any later sprint adds new
apps/permissions) — it's idempotent, so re-running is always safe:

    python manage.py migrate
    python manage.py seed_role_permissions
"""
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from apps.accounts.models import Role

# (app_label, codename) pairs. Extend this dict as later sprints add apps —
# do not edit historical migrations to do this.
ADMINISTRATOR_PERMS = [
    ("accounts", "manage_users"),
    ("accounts", "manage_roles"),
    ("settings_app", "change_pharmacysettings"),
    ("settings_app", "view_pharmacysettings"),
    ("settings_app", "change_numberingsequence"),
    ("settings_app", "view_numberingsequence"),
]
PHARMACIST_PERMS = []
CASHIER_PERMS = []


class Command(BaseCommand):
    help = "Seeds/refreshes permission sets on the four default Roles."

    def handle(self, *args, **options):
        owner = Role.objects.filter(name="Owner").first()
        if owner:
            owner.group.permissions.set(Permission.objects.all())
            self.stdout.write(self.style.SUCCESS("Owner: granted all permissions."))

        for role_name, perm_list in [
            ("Administrator", ADMINISTRATOR_PERMS),
            ("Pharmacist", PHARMACIST_PERMS),
            ("Cashier", CASHIER_PERMS),
        ]:
            role = Role.objects.filter(name=role_name).first()
            if not role:
                self.stdout.write(self.style.WARNING(f"{role_name}: role not found, skipped."))
                continue
            perms = Permission.objects.filter(
                content_type__app_label__in={a for a, _ in perm_list},
                codename__in={c for _, c in perm_list},
            ) if perm_list else Permission.objects.none()
            role.group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"{role_name}: {perms.count()} permissions assigned."))
