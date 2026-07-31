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
from django.db.models import Q

from apps.accounts.models import Role, User

# (app_label, codename) pairs. Extend this dict as later sprints add apps —
# do not edit historical migrations to do this.
_INVENTORY_MODELS = ["category", "manufacturer", "dosageform", "unit", "drug"]
_INVENTORY_FULL_ACCESS = [
    ("inventory", f"{action}_{model}")
    for model in _INVENTORY_MODELS
    for action in ("add", "change", "delete", "view")
]

# Sprint 3: stock is shared infrastructure (see Sprint 3 Implementation
# Plan) — Cashier gets none of this, matching the Permissions Matrix.
_STOCK_MANAGE_ACCESS = [
    ("stock", "add_stockadjustment"),
    ("stock", "view_stockadjustment"),
    ("stock", "view_inventorymovement"),
]

_CUSTOMERS_FULL_ACCESS = [
    ("customers", f"{action}_customer") for action in ("add", "change", "delete", "view")
]
# Cashier: view/create only, no delete — per the Permissions Matrix.
_CUSTOMERS_CASHIER_ACCESS = [
    ("customers", "add_customer"),
    ("customers", "view_customer"),
]

# `change_sale`/`delete_sale` are Django's auto-created defaults but no
# view anywhere uses them (a Sale is only ever created via checkout or
# cancelled via cancel_sale) — deliberately not granted to anyone but
# Owner, so no role appears to have a capability the UI never exposes.
_SALES_FULL_ACCESS = [
    ("sales", "add_sale"),
    ("sales", "view_sale"),
    ("sales", "cancel_sale"),
    ("sales", "view_all_sales"),
]
_SALES_CASHIER_ACCESS = [
    ("sales", "add_sale"),
    ("sales", "view_sale"),
]

ADMINISTRATOR_PERMS = [
    ("accounts", "manage_users"),
    ("accounts", "manage_roles"),
    ("settings_app", "change_pharmacysettings"),
    ("settings_app", "view_pharmacysettings"),
    ("settings_app", "change_numberingsequence"),
    ("settings_app", "view_numberingsequence"),
    *_INVENTORY_FULL_ACCESS,
    *_STOCK_MANAGE_ACCESS,
    *_CUSTOMERS_FULL_ACCESS,
    *_SALES_FULL_ACCESS,
]
# Pharmacist: "Handles inventory, sales and drug-related workflows" (Blueprint)
# — full inventory/stock/customer/sales management, no user/role/settings access.
PHARMACIST_PERMS = [
    *_INVENTORY_FULL_ACCESS,
    *_STOCK_MANAGE_ACCESS,
    *_CUSTOMERS_FULL_ACCESS,
    *_SALES_FULL_ACCESS,
]
# Cashier: "Handles point-of-sale transactions only" (Blueprint) — read-only
# drug lookup, own-sales-only POS/history (row-level scoping is enforced in
# sales_service.get_sales_queryset, not by permission), and no stock access.
CASHIER_PERMS = [
    ("inventory", "view_drug"),
    *_CUSTOMERS_CASHIER_ACCESS,
    *_SALES_CASHIER_ACCESS,
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
            if perm_list:
                # Bug fix: the previous independent app_label__in / codename__in
                # filters matched any (app_label, codename) cross-product, not
                # exact pairs — harmless only because no codename happened to
                # collide across apps yet. Built as proper OR-of-exact-pairs
                # now that more apps exist.
                query = Q()
                for app_label, codename in perm_list:
                    query |= Q(content_type__app_label=app_label, codename=codename)
                perms = Permission.objects.filter(query)
            else:
                perms = Permission.objects.none()
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
