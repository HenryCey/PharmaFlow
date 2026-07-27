# Changelog

All notable changes to PharmaFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
