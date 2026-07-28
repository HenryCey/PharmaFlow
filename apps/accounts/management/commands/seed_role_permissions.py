"""
Assigns baseline permissions to the four default Roles, and (as of the
Sprint 2 permissions bug fix) backfills existing users' Group membership
to match their Role.

Run this once after `migrate` (and again after any later sprint adds new
apps/permissions, or after the bug-fix below is deployed) — it's
idempotent, so re-running is always safe:

    python manage.py migrate
    python manage.py seed_role_permissions
"""
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User

# (app_label, codename) pairs. Extend this dict as later sprints add apps —
# do not edit historical migrations to do this.
_INVENTORY_MODELS = ["category", "manufacturer", "dosageform", "unit", "drug"]
_INVENTORY_FULL_ACCESS = [
    ("inventory", f"{action}_{model}")
    for model in _INVENTORY_MODELS
    for action in ("add", "change", "delete", "view")
]

ADMINISTRATOR_PERMS = [
    ("accounts", "manage_users"),
    ("accounts", "manage_roles"),
    ("settings_app", "change_pharmacysettings"),
    ("settings_app", "view_pharmacysettings"),
    ("settings_app", "change_numberingsequence"),
    ("settings_app", "view_numberingsequence"),
    *_INVENTORY_FULL_ACCESS,
]
# Pharmacist: "Handles inventory, sales and drug-related workflows" (Blueprint)
# — full inventory management, no user/role/settings access.
PHARMACIST_PERMS = [*_INVENTORY_FULL_ACCESS]
# Cashier: "Handles point-of-sale transactions only" (Blueprint) — read-only
# drug lookup only, needed to search/sell a drug once POS (Sprint 3) exists.
CASHIER_PERMS = [
    ("inventory", "view_drug"),
]


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

        # Sprint 2 permissions bug fix: User.role (FK) and User.groups (the
        # M2M ModelBackend actually reads for has_perm()) were never kept in
        # sync before User.save() was fixed. That fix only takes effect on
        # future saves, so existing rows need a one-time backfill here.
        synced = 0
        for user in User.objects.filter(role__isnull=False):
            user.groups.set([user.role.group])
            synced += 1
        cleared = 0
        for user in User.objects.filter(role__isnull=True).exclude(groups=None):
            user.groups.clear()
            cleared += 1
        self.stdout.write(self.style.SUCCESS(
            f"Group membership: synced {synced} user(s) to their role's group"
            + (f", cleared {cleared} unassigned user(s)." if cleared else ".")
        ))
