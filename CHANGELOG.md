# Changelog

All notable changes to PharmaFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.0] - 2026-07-28

Sprint 2 (Inventory Management) delivery per the Development Roadmap. Sprint 1 continues to work exactly as before — no Sprint 1 files were changed except `config/settings/base.py`, `config/urls.py`, `templates/layout/partials/_sidebar.html`, `apps/accounts/models.py`, and `apps/accounts/management/commands/seed_role_permissions.py` (see Fixed, below, for why the last two were touched).

**Versioning note:** the Sprint 2 Build Request originally asked for this release to be tagged `v0.2.0`. Per the project's own Versioning Policy ("Sprint 2 Complete → v1.1.0") and by agreement, this release is tagged `v1.1.0` instead, continuing directly from `v1.0.3`.

### Added

- New `apps/inventory` app (added to `INSTALLED_APPS`, wired into `config/urls.py` under `/inventory/`).
- **Category** CRUD (`Category`: name, description, status) — Database Spec's "Drug Categories".
- **Manufacturer** CRUD (`Manufacturer`: name, description, status) — new lookup table, not in the original Database Spec but explicitly requested in the Sprint 2 Build Request; purely additive, referenced by `Drug.manufacturer` (nullable).
- **Dosage Form** CRUD (`DosageForm`: name, description, status) — Tablet, Capsule, Syrup, Injection, Cream, Suspension, Drops, etc.
- **Unit** CRUD (`Unit`: name, description, status) — Tablet, Bottle, Carton, Pack, Strip, Tube, Piece, etc.
- **Drug** (Drug Products) CRUD: name, generic name, brand name, SKU, barcode, category, manufacturer, dosage form, unit, strength, description, cost price, selling price, minimum stock, reorder level, status, created by/at/updated at. Inherits `SoftDeleteModel` (like `User`) so discontinued drugs are preserved for future Sales/Purchases history rather than hard-deleted.
- **Barcode**: plain `CharField`, unique and nullable — supports both manual typing and USB barcode scanner input (scanners act as a keyboard, so no special integration code is needed). No barcode image generation or printing, per scope.
- **Drug list**: search (name, generic name, brand name, SKU, barcode), filters (Category, Manufacturer, Status, Low Stock), column sorting (Name, Cost Price, Selling Price, Stock, asc/desc), and pagination (20/page), all via querystring parameters so filters/sort/search compose together and are shareable/bookmarkable links.
- **Drug detail page**: full read view of all fields plus KPI-style cards (Selling Price, Cost Price, Current Stock, Reorder Level).
- Sidebar: "Inventory" is now a real expandable section for any user with `inventory.view_drug`; still shows as a disabled placeholder for anyone without it. Sales/Purchases/Customers/Suppliers/Reports remain "Coming soon" placeholders, unchanged.
- `seed_role_permissions`: Administrator and Pharmacist now receive full add/change/delete/view on all five inventory models; Cashier receives `view_drug` only (read-only drug lookup, anticipating Sprint 3's POS). Owner is unaffected (already has all permissions).
- Read-only users see no Add/Edit/Delete controls anywhere in the module (permission-gated in both views and templates), per the Sprint 2 Build Request.

### Changed

- Sidebar's Inventory sub-links (Categories, Manufacturers, Dosage Forms, Units) are now each individually permission-gated (`inventory.view_category`/`view_manufacturer`/`view_dosageform`/`view_unit`), instead of only the top-level "Inventory" section being gated on `view_drug`. Previously, a Cashier (who has only `view_drug`) would see all five sub-links but get a 403 on four of them; the sidebar now only ever shows links the current user can actually open.

### Fixed

Issues found and corrected during release hardening (`makemigrations`/`migrate`/`check` verification), before this version was tagged:

- **Migration drift on `Category`/`Drug` (`makemigrations` was not clean).** Both models explicitly declared a no-op `permissions = []` in `Meta`. Django's autodetector records any Meta attribute that was explicitly assigned on the class, even when its value equals the framework default, so this showed up as a real difference against the hand-written `0001_initial.py` (which had no `permissions` key at all). Removed the redundant lines from `models.py` — `Meta` now matches the migration exactly, with no schema change needed.
- **Non-superuser roles could not access anything, regardless of assigned permissions (the "permissions bug").** `User.role` (a plain FK) and `User.groups` (the M2M Django's `ModelBackend` actually reads for `has_perm()`) were never connected anywhere in the codebase — a pre-existing Sprint 1 gap that Sprint 2's first real permission-gated views exposed. It went unnoticed in Sprint 1 because Owner accounts are created via `create_superuser`, and Django's permission checks short-circuit to `True` for superusers regardless of group membership. Fixed by having `User.save()` sync `self.groups` to `[self.role.group]` on every save (mirroring `Role.save()`'s existing invariant-enforcement pattern). `seed_role_permissions` now also backfills existing users' group membership in the same run, since the `save()` fix only applies to future saves.
- **Filter button on the Drug list did nothing (Enter still worked).** The template wrapped the `_button.html` include — which renders its own `<button type="button">` by default — inside another `<button type="submit">`, producing invalid nested `<button>` markup. Browsers auto-close the outer button when parsing hits the inner one, leaving the non-submitting inner button as the actual clickable element. Fixed by passing `type="submit"` directly into the include, matching the pattern already used correctly elsewhere (e.g. `category_form.html`).
- **"Out of Stock"/"Low Stock" badge wrapped onto two lines for some roles but not others.** The stock number and badge were rendered as plain space-separated inline content in a table cell with no wrapping container. With the table's default `table-layout: auto`, a wider Actions column (Admin/Pharmacist see "View / Edit / Discontinue"; Cashier sees only "View") compressed the Stock column's available width enough to wrap the badge onto a second line; Cashier's narrower Actions column happened to leave enough room not to. Fixed by wrapping the number and badge in a single `inline-flex items-center gap-1.5 whitespace-nowrap` span, so the cell renders as one atomic unit regardless of a given role's Actions column width.

### Known Limitations

- **Current Stock is not yet editable anywhere in the UI.** The Technical Architecture requires stock quantity to be written only inside the same transaction as an `InventoryMovement` (Purchase, Sale, or Stock Adjustment) — none of which exist yet (they're excluded from Sprint 2 scope). `Drug.current_stock` is a real field (defaults to `0`) but is intentionally excluded from `DrugForm` and shown read-only on the form/detail pages. Every drug will show as "Low Stock" and/or "Out of Stock" until the `stock` app is built — this is expected, not a bug.
- No barcode image generation, printing, or scanner-driver integration — barcode is a manual/scanner-typed text field only, per scope.
- No Suppliers or Purchases yet, so a Drug's Category/Manufacturer/Dosage Form/Unit can only be managed through this module's own lookup CRUD screens.
- Category/Manufacturer/Dosage Form/Unit deletion is a hard delete (blocked with a friendly message if a Drug still references it) rather than a soft delete — these are simple lookup tables with no history of their own, following the same precedent as `Role` in Sprint 1. `Drug` deletion is a soft "Discontinue" action, following the same precedent as `User` deactivation.

### Upgrade Notes

```bash
python manage.py migrate
python manage.py seed_role_permissions
```

No destructive schema changes. `seed_role_permissions` is idempotent and safe to re-run; existing custom roles you've created yourself are untouched (only the four default roles are updated), and it will also correct group membership for any existing users created before this release.

## [v1.0.3] - 2026-07-27

Fixes `makemigrations`/`migrate` reporting unreflected model changes for `accounts` and `settings_app`. No models were changed — the migrations were hand-written (this project's sandbox has no network access to run Django directly) and had drifted from the models' true state since Sprint 1. This release corrects the migrations only.

### Fixed

- **`accounts`: `User.groups` help_text mismatch.** `User.groups` is inherited unmodified from `django.contrib.auth.models.PermissionsMixin`, whose real help_text is *"The groups this user belongs to. A user will get all permissions granted to each of their groups."* The hand-written `0001_initial.py` truncated this to just the first sentence, so the recorded migration state never matched the model's actual (inherited) state. Added `0004_alter_user_groups_help_text.py` with the correct, complete help_text.
- **`settings_app`: two missing `help_text` values.** `PharmacySettings.currency_symbol` and `NumberingSequence.padding` have carried a `help_text` in `models.py` since Sprint 1, but the hand-written `0001_initial.py` omitted both. Added `0003_alter_pharmacysettings_currency_symbol_and_more.py` to bring the migration state in line with the models.

### Verification

Confirmed field-by-field, model-by-model, migration-by-migration for both apps (every field's type, `null`, `blank`, `unique`, `default`, `choices`, `help_text`, `verbose_name`, `on_delete`, `related_name`, and every model's `Meta` options) that model state and migration state now match exactly. `python manage.py makemigrations` is expected to report:

```
No changes detected
```

### Notes for upgrading from v1.0.2

```bash
python manage.py migrate
```

Both new migrations only change `help_text` metadata (a Python/admin-facing string, not stored in the database) — no schema or data changes, safe to apply at any time.



Sprint 1 final QA fixes. No functionality changed beyond what's listed below — still Sprint 1 scope only.

### Fixed

- **Editing a user's password left them unable to log in.** `set_password()` and the "leave blank to keep the existing password" behavior in `UserForm.save()` were already implemented correctly (verified by tracing Django's `ModelForm._post_clean()`, which already excludes `password` from `Meta.fields` so it's never overwritten with plaintext). The actual reproducible cause: the password `<input>` had no `autocomplete` hint, so the browser would silently autofill it with a different saved credential, which then got hashed and saved as though it were intentional. Added `autocomplete="new-password"` to the field's widget, and now strip incidental whitespace before deciding whether a password was actually entered.
- **Change Password was unreachable from the UI.** The view, URL (`accounts:password_change`), and template already existed and worked correctly — but nothing in the app linked to it, so it was effectively invisible. Replaced the static user-info block in the header with a working dropdown menu (using Alpine, consistent with the rest of the app) exposing **Change Password** and **Logout**.
- **A sidebar template comment rendered as visible text.** The comment used `{# ... #}`, which does not support multi-line content — Django's tag regex only matches `{#...#}` within a single line, so a comment spanning three lines fell through and was output as literal text instead of being stripped. Replaced with `{% comment %}...{% endcomment %}`, which handles multi-line content correctly. Audited every other template for the same pattern; no other instances found.
- **Logout button misaligned in the sidebar.** Its wrapping `<div>` had its own `p-3` padding stacked on top of the button's own `px-2 py-2`, making it narrower and inset differently than every other sidebar item (`px-5 py-2.5`). Rebuilt it with the exact same `flex items-center gap-3 px-5 py-2.5` pattern used by every nav link, so its spacing, width, and hover highlight now match exactly.

### Notes for upgrading from v1.0.1

```bash
python manage.py migrate   # no new migrations in this release
```

No database changes in this release — template, form, and settings changes only.



Sprint 1 bug-fix pass following local testing on Windows + PostgreSQL. No new features — Sprint 2 has not started.

### Fixed

- **Login button unstyled until hover.** `login.html` loaded the Tailwind CDN script without the custom theme config (`primary`/`danger`/`warning`/`success` colors) that `base.html` defines, so `bg-primary` resolved to no CSS at all. Extracted the Tailwind CDN script + color config into one shared partial (`templates/layout/partials/_tailwind_cdn.html`) included by both pages, and had the login page also load `app.css` so its input fields match the rest of the app.
- **User deactivation didn't change the displayed status.** The "Deactivate" action called a soft-delete (`is_deleted`/`deleted_at`), which never touches the `status` field the Users list actually renders — so a successful deactivation still showed "Active." The action now sets `status = inactive` directly, matching the button's own label and the confirmation page's own copy. Updated the confirmation page text to describe what actually happens (blocked from login, remains visible in the list as Inactive) instead of the previous "removed from active lists" wording, which was no longer accurate.
- **`User.objects` silently ignored soft-deletes.** The custom `UserManager` (needed for `create_user`/`create_superuser`) had fully replaced `SoftDeleteModel`'s manager, so `User.objects.all()` never filtered out soft-deleted rows, unlike every other soft-deletable model. `UserManager.get_queryset()` now applies the same alive()-only filtering.
- **`.env` file was never loaded.** `config/settings/base.py` read `os.environ.get(...)` for DB credentials and secret key but nothing ever called `load_dotenv()`, so a project with a `.env` file silently fell back to the hardcoded defaults. Added `from dotenv import load_dotenv` and `load_dotenv(BASE_DIR / ".env")` at the top of `base.py`. (`python-dotenv` was already present in `requirements.txt`.)
- **Uploaded pharmacy logo had nowhere to resolve.** `PharmacySettings.logo` is an `ImageField`, but `MEDIA_URL`/`MEDIA_ROOT` were never defined anywhere. Added both to `base.py` and wired `static(settings.MEDIA_URL, ...)` into `config/urls.py` for local/dev serving.
- **`LoginHistory.user` cascaded on delete.** A hard-deleted `User` row would have silently taken its entire login audit trail down with it, contradicting the Blueprint's "maintain complete activity history" rule. Changed `on_delete` from `CASCADE` to `SET_NULL` (field was already nullable) and added migration `0003_loginhistory_user_on_delete_set_null`.
- **Deleting a Role orphaned its Group.** `Role` wraps `auth.Group` 1:1, but deleting a `Role` left the underlying `Group` row behind with no owner. `Role.delete()` now removes its linked `Group` too.
- **Dead middleware entry.** `apps.accounts.middleware.LoginHistoryMiddleware` existed only to force-import the login-history signal module — but `AccountsConfig.ready()` already does exactly that. Removed the unused middleware class and its entry from `MIDDLEWARE`; the signal receivers are unaffected and still fire on every login attempt.

### Changed

- Sidebar tooltips ("Coming in a later sprint"), the notification bell tooltip ("Notifications (Sprint 4)"), dashboard KPI card captions ("Live in Sprint 3/4"), and a Role-form hint referencing the Django admin screen all exposed internal roadmap/implementation language to end users. Replaced with neutral, user-appropriate copy ("Coming soon" / a description that doesn't name internal tooling).

### Notes for upgrading from v1.0.0

```bash
pip install -r requirements.txt   # no new dependencies, but re-run is harmless
python manage.py migrate          # applies migration 0003 (LoginHistory.user on_delete)
```

No data loss is expected. Any users previously "deactivated" under the old (soft-delete) behavior were hidden from the list entirely rather than marked Inactive — check for any such accounts and restore them manually if they should now appear as Inactive instead of hidden:

```python
from apps.accounts.models import User
User.all_objects.filter(is_deleted=True).update(is_deleted=False, deleted_at=None, status=User.STATUS_INACTIVE)
```

## [v1.0.0] - 2026-07-27

Initial Sprint 1 (Foundation) delivery per the Development Roadmap.

### Added

- Project scaffold: `config/settings/{base,development,production}.py`, environment-driven PostgreSQL configuration.
- `apps/common`: `TimeStampedModel`, `SoftDeleteModel`/`SoftDeleteManager`, shared permission mixin.
- `apps/accounts`: custom `User` model, `Role` (wraps `auth.Group`), `LoginHistory`, login/logout, password change, User CRUD, Role CRUD, four default roles (Owner, Administrator, Pharmacist, Cashier) seeded via migration, `seed_role_permissions` management command.
- `apps/settings_app`: `PharmacySettings` (singleton), `NumberingSequence` with an atomic `generate_document_number()` service, single-currency configuration defaulting to ₦.
- `apps/dashboard`: placeholder landing page.
- One application shell (`templates/layout/`) and a reusable component library (`templates/components/`) per the UI Contract.
