"""
reports models.

This app is deliberately model-less: every number it shows is computed
on demand (via apps/reports/services/) from data that already lives in
`sales`, `purchases`, `stock`, `inventory`, `customers` and `suppliers`.
There is nothing here for `reports` itself to own or persist.

Django's permission system, however, is model-based — `@permission_required`
checks always resolve against a (app_label, codename) pair tied to a
ContentType. Since PharmaFlowPermissionMixin (apps/common/permissions.py)
is the established pattern for every other app's route-level access
control, report views need the same mechanism to plug into, without a
real table behind it. `ReportAccess` is a permission-only marker model —
`managed = False` means Django's SchemaEditor never emits any DDL for it
(no `CREATE TABLE`, ever), so it adds no real table to the database.

A migration (0001_initial) still exists for it, which is expected and
correct: `makemigrations` must track the model's *state* even though
`managed = False` skips its *schema* — this is what lets `migrate`'s
post-migrate signal register the model's ContentType and create the
permissions below, exactly like `accounts.User`'s `manage_users` /
`manage_roles` permissions that aren't tied to a CRUD action either.
Re-running `makemigrations` after this file reports "No changes
detected", same as any other stable model.
"""
from django.db import models


class ReportAccess(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("view_inventory_reports", "Can view inventory reports"),
            ("view_sales_reports", "Can view sales reports"),
            ("view_purchase_reports", "Can view purchase reports"),
            ("view_financial_reports", "Can view financial reports"),
        ]
