# Changelog

All notable changes to PharmaFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.3.0] - 2026-08-04

Sprint 4 (Purchasing & Supplier Management) — official release. Completes the inventory lifecycle Sprint 3 left half-finished: Supplier → Purchase Order → Goods Receipt → Inventory Ledger. Sprint 1–3 continue to work exactly as before; every change to already-released files was additive wiring or a targeted bug fix (see Fixed, below).

**Architecture note:** two new apps this sprint — `apps/suppliers` and `apps/purchases` — matching the original Technical Architecture's app split. Receiving a Purchase Order writes to the same `InventoryMovement` ledger Sales already uses (a new `purchase` movement type extends `stock`, per the Sprint 3 comment that anticipated exactly this), never touching `Drug.current_stock` directly. No existing module was redesigned to make room for this.

### Added

- **`apps/suppliers`**: full CRUD (Supplier Name, Contact Person, Phone, Email, Address, City, State, Country, Status, Notes), soft-deletable. Auto-generated Supplier Code, reusing the existing `NumberingSequence` service (a new `supplier_code` sequence, added via additive migrations — the historical seed migration was never edited). Detail page shows Purchase History, Total Purchases, Outstanding Purchases, and Last Purchase.
- **`apps/purchases`**: `PurchaseOrder`/`PurchaseItem` with a full Draft → Ordered → Received/Cancelled lifecycle. Business logic split per the established pattern: `purchase_service.py` (lifecycle — create/edit Draft, Place Order, Cancel — never touches the ledger) and `receiving_service.py` (the one action that does).
- **Batch tracking**: each Purchase Item carries Batch Number, Manufacturing Date, Expiry Date, Unit Cost, and Selling Price — laying groundwork for future expiry management (see Known Limitations).
- **Multi-item Purchase Order form**: a Django formset with Alpine-driven dynamic row add/remove, plus a true live-filtering searchable Drug selector (type-to-filter, click to select — see Fixed for the two rounds of bugs this went through).
- **Purchase Order actions dropdown** on the list view, status-driven exactly per spec (Draft: View/Edit/Place Order/Cancel; Ordered: View/Receive/Print; Received/Cancelled: View/Print) — reuses the existing `_dropdown.html` component from Sprint 3's Drug List redesign.
- **Printable Purchase Order** (on-screen + browser print), following the same scoped-print-CSS pattern as Sales' receipt.
- **Recently Received Stock** operational report — a lightweight, non-BI list of recently received purchase items, per Sprint 4's explicit "operational reports only" scope.
- Sidebar: "Purchases" (Purchase Orders / Recently Received) and "Suppliers" are now real, permission-gated entries.
- `seed_role_permissions` extended: Administrator gets full access to both new apps; Pharmacist gets Create/Edit/Receive Purchases and view-only Suppliers (no Cancel, no Supplier management) — an intentional narrowing versus every other module this role otherwise fully manages, per the Build Request's explicit permissions list; Cashier gets no access to either app.
- **Offline-first static assets**: Tailwind CSS is now compiled ahead of time into a single local `static/css/tailwind.css` (via a real, offline Tailwind CLI build scanning every template *and* every `apps/**/*.py` file, since some views construct Tailwind-classed HTML directly in Python) instead of loading `cdn.tailwindcss.com` at runtime — matching what the original Technical Architecture always specified. HTMX and Alpine.js are now bundled directly as `static/vendor/htmx.min.js` and `static/vendor/alpinejs.min.js` — no CDN, no manual download step, works immediately on a fully offline pharmacy LAN. See Known Limitations for the one version-pinning caveat.
- New `_searchable_select.html` shared component: a reusable live-filtering combobox wrapper for any `<select>` field, without altering the underlying select's name/id/options/value — Django form parsing and POST data are unaffected by design.
- New `FUTURE_ENHANCEMENTS.md` backlog, documenting the "Last Cost Wins" costing decision (see Known Limitations) as the first entry.

### Changed

- **Drug list Actions column** (Sprint 3) — no change this sprint; mentioned here only because Purchase Order's new Actions dropdown directly reuses that same pattern/component.
- **`Drug.objects` uniqueness checks**: `DrugForm` and `CustomerForm` now validate SKU/Barcode/Phone uniqueness explicitly against `all_objects` instead of relying solely on Django's built-in `validate_unique()` — see Fixed, below, for why.

### Fixed

Issues found and corrected across five QA rounds this sprint, before this version was tagged:

- **Formset display bug**: `min_num=1` combined with `extra=1` on the Purchase Item formset would have shown 2 blank rows on a new Purchase Order instead of 1 (Django adds these counts together in `total_form_count()`). Fixed by removing `min_num` and enforcing "at least one item" via a custom formset `clean()` instead.
- **Formset row-removal bug**: the original "Remove" button deleted a row's DOM node entirely, which — for an *existing* (already-saved) item during editing — strips its required fields from POST and triggers validation errors instead of a clean deletion. Fixed to use the formset's real `DELETE` checkbox (hide + check), matching why Django's `can_delete` mechanism exists in the first place.
- **Migration drift on `stock`**: `InventoryMovement.Meta.indexes` had no explicit `name=`, so Django auto-computed a hash-based index name at migration-check time that didn't match the human-readable name manually written into the hand-crafted migration. Fixed by naming the index explicitly in the model — same root-cause shape as prior sprints' Meta-options drift, this time for `indexes`.
- **Duplicate SKU/Barcode/Phone produced a raw `IntegrityError`, not a friendly message.** Root cause: `Drug.objects`/`Customer.objects` (the default manager Django's `validate_unique()` uses) are alive-only (`SoftDeleteManager`) — a discontinued/deleted record's SKU, barcode, or phone is invisible to that check but still occupies the real DB constraint, so the check passed and the raw constraint violation surfaced instead. Fixed with explicit checks against `Drug.all_objects` / `Customer.all_objects` in each form's `clean_<field>()`.
- **Expired stock could be received into inventory.** Business rule enforced at the earliest point (`PurchaseItemLineForm.clean_expiry_date()`): `expiry_date <= today` is rejected with a friendly message — tightened from an initial `<` to the correct `<=` after a QA round caught that a batch expiring *today* was still being accepted.
- **Three separate nested-`<button>` bugs** (Clear Cart, both Receipt Print buttons, and the Purchase Item "+ Add Item" button) — same bug class as Sprint 2's original Filter button fix: a `<button>` wrapping another `<button>` via the shared `_button.html` component is invalid HTML, and browsers auto-close the outer (behavior-carrying) element when the parser hits the inner one. Fixed by rendering these buttons directly instead of wrapping the component. **A project-wide scan confirms zero nested-button instances remain anywhere in the codebase.**
- **Searchable Drug Selector — two rounds of real bugs, not asset-loading issues:**
  1. Initial version required Enter/a visible Search button and didn't filter live — rebuilt as a true combobox (type → live-filtered dropdown → click to select, `Enter` explicitly prevented from submitting the form) while keeping the real `<select>` completely unchanged for 100% POST-structure compatibility.
  2. After that rebuild, clicking a filtered result did nothing. Root cause: Alpine's `$el` magic property resolves to *whichever element the current directive is declared on*, not a fixed reference to the component's root — `choose()`/`revert()` were being invoked from directives on nested descendant elements (a dropdown item; the `.relative` wrapper), so `this.$el.querySelector('select')` found nothing there and silently failed. Fixed by caching the select element once in `init()` (where `$el` is guaranteed correct) as a plain object property, referenced everywhere else instead of re-deriving via `$el`.
- **Offline asset loading**: the application silently lost all CSS/JS styling and interactivity whenever the pharmacy's LAN had no internet access, because Tailwind, HTMX, and Alpine.js were all loaded from external CDNs. Fixed as described in Added, above — genuinely bundled, not just reconfigured to point at a still-missing local path.
- **Purchase Item layout**: fields were visually compressed, and Expiry Date was squeezed into a 1/12-width column while Manufacturing Date awkwardly took a full-width row of its own. Rebuilt into two clearer, evenly-spaced rows — no fields added or removed, no other layout changes.
- **Purchase Orders list discoverability**: after saving a Draft, there was no obvious way back to it besides knowing the Purchase Number itself was a clickable link. Fixed via the new Actions dropdown (see Added).

### Improvements

- **Opening Stock UX**: the Adjust Stock form (Sprint 3) now defaults Adjustment Type to Opening Stock and shows a contextual helper message when a drug's current stock is exactly 0 — reduces friction during initial inventory setup. (Carried over from a Sprint 4 QA round; noted here since it shipped alongside this release.)
- **"Company Name" → "Supplier Name"**: form label only — `company_name` remains the real field/column name, so no migration was needed. Not every supplier is a registered company (e.g. "Blessing Ventures", "Ngozi Drug Depot").
- **Country defaults to Nigeria** on the Supplier form (form-level `initial=`, not a model `default=`, which would have required its own migration) — still fully editable.

### Known Limitations

- **"Last Cost Wins" costing method** — receiving a Purchase Order overwrites `Drug.cost_price`/`selling_price` with the most recently received batch's values, rather than a weighted average, FIFO, or supplier-specific pricing. Deliberate, documented Sprint 4 scope decision — see `FUTURE_ENHANCEMENTS.md` for the full writeup and recommended future work (Weighted Average Cost, FIFO, batch-aware/FEFO selling at POS).
- **Vendored JS version note**: `static/vendor/htmx.min.js` and `alpinejs.min.js` are htmx 1.9.10 and Alpine 3.10.5 — the closest versions independently retrievable and verified in the build environment, rather than the originally-pinned 1.9.12/3.13.5. Same public API; nothing in this codebase depends on version-specific behavior between these releases. See `static/vendor/README.md`. A drop-in file swap if the exact pinned versions are ever needed.
- Manual Batch Number entry only — no auto-generation or barcode scanner integration for batches (explicitly deferred per the Build Request; acceptable for this sprint).
- Purchase Returns are part of the long-term inventory lifecycle but not built this sprint — the ledger's `movement_type` intentionally does not yet include a `purchase_return` value; it will be added alongside that feature when it ships.
- Same Sprint 2/3 limitations still apply where unaffected by this sprint (hard-delete on lookup tables, no barcode imaging, no full Reports engine — still Sprint 5+ scope, no Global Search — still deferred, no PDF/WeasyPrint receipt or Purchase Order export).

### Upgrade Notes

```bash
python manage.py migrate
python manage.py seed_role_permissions
```

No destructive schema changes. `seed_role_permissions` remains idempotent and safe to re-run. If deploying to an existing environment with `collectstatic` in the pipeline, re-run it once so the newly bundled `static/vendor/` and `static/css/tailwind.css` files are picked up.

## [v1.2.0] - 2026-07-29

Sprint 3 (Sales Module) delivery per the Sprint 3 Implementation Plan. Sprint 1/2 continue to work exactly as before — no existing module was redesigned; every change to already-released files was additive wiring or a targeted bug fix (see Fixed, below).

**Architecture note:** Sprint 3 added a third new app, `apps/stock`, beyond what the original Build Request literally listed. This was a deliberate, approved addition — the Technical Architecture requires stock quantity to be written only inside the same transaction as an `InventoryMovement` (Purchase, Sale, or Stock Adjustment), and Sprint 2 had left `Drug.current_stock` read-only specifically pending this. `stock` is treated as shared infrastructure required by Sales, not a standalone business module — it has no sidebar entry of its own; it's reached from the Drug detail/list pages in `apps/inventory`.

### Added

- **`apps/customers`**: `Customer` CRUD (name, phone, address), soft-deletable, with purchase history shown on the detail page. Walk-in customers are not a database row — `Sale.customer` is simply nullable.
- **`apps/stock`** (shared infrastructure): `InventoryMovement` (append-only ledger, the single source of truth for stock quantity) and `StockAdjustment` (Opening Stock, Damage, Expired, Lost, Correction). `record_movement()` is the *only* function anywhere in the project permitted to write `Drug.current_stock`. Reached via "Adjust Stock" (Drug list row action and Drug detail page) and a "Movement History" section on the Drug detail page.
- **`apps/sales`**: `Sale`/`SaleItem` models (custom permissions `cancel_sale`, `view_all_sales`, alongside the standard CRUD ones). Business logic split into four focused service modules per the approved refinement: `cart_service.py` (session-scoped cart), `checkout_service.py` (the atomic checkout transaction), `receipt_service.py` (receipt render context), `sales_service.py` (cancellation, row-scoped history, daily summary).
- **POS**: drug search (name/generic name/brand name/SKU/barcode) with an HTMX-powered cart — the first real use of `hx-post` in this project; added the necessary CSRF header wiring to `base.html` to support it.
- **Checkout**: customer selection (optional — walk-in by default), payment method, discount; atomically deducts stock per line and rolls back the entire sale if any line can't be fulfilled.
- **Sales History**: row-level scoped — a Cashier sees only their own sales; `sales.view_all_sales` (Owner/Administrator/Pharmacist) sees everyone's.
- **Sale Cancellation**: reverses stock via a new ledger movement (the original sale movements are never edited/deleted — the ledger is append-only); Cashier cannot cancel.
- **Receipt**: on-screen + separate Thermal/A4 print stylesheets, reusing the existing `NumberingSequence.generate_document_number("sale_receipt")` service (already seeded since Sprint 1, unchanged).
- **Today's Sales**: a deliberately lightweight daily summary (count, revenue, top-selling drugs) — not the full parameterized Reports engine (date ranges, PDF export, Profit/Inventory/Expiry reports), which stays Sprint 4 scope per the Feature Specs.
- Sidebar: "Sales" (Point of Sale / Sales History / Today's Sales) and "Customers" are now real, permission-gated entries. Purchases/Suppliers/Reports remain "Coming soon" placeholders.
- `seed_role_permissions` extended for `stock`/`customers`/`sales`; Administrator and Pharmacist get full management access, Cashier gets POS + own-history + read-only drug lookup only, per the Sprint 3 Permissions Matrix.

### Changed

- **Drug list Actions column** redesigned as a compact "Actions ▾" dropdown (reusing the existing `_dropdown.html` component) instead of concatenated inline links, which wrapped unreadably once a 4th action ("Adjust Stock") was added. Destructive actions (Discontinue) render in red; normal actions stay plain — `_dropdown.html` gained optional per-item `danger` styling to support this.
- **Row numbering** added to the shared `_table.html` component — applies automatically to all 8 list views in the project (Users, Roles, Drugs, Categories, Manufacturers, Dosage Forms, Units, Customers) with no per-view changes, and continues correctly across pages rather than resetting to 1.
- **Every list search box** in the project now has a visible Search button next to the input (previously Enter-only): Users, Categories, Manufacturers, Dosage Forms, Units, Customers, and POS. (Drug list already had one, since it also has dropdown filters requiring an explicit "apply" action.)
- **Global Search box** in the header (visible but never implemented, inherited from Sprint 1's UI shell) is now disabled with a "coming soon" affordance, matching the sidebar's existing placeholder convention — prevents it from looking broken before Global Search is actually built.
- **Stock Adjustment form**: replaced the previous implicit signed-quantity entry with an explicit **Direction** (Increase/Decrease) field plus a magnitude-only Quantity — see Fixed, below, for the bug this corrects. When a drug's current stock is exactly 0, the form now defaults Adjustment Type to Opening Stock (Direction: Increase) and shows a contextual helper message, reducing friction during initial inventory setup.

### Fixed

Issues found and corrected during Sprint 3's QA rounds, before this version was tagged:

- **Migration drift on `stock` (`makemigrations` was not clean).** `InventoryMovement.Meta.indexes` had no explicit `name=`, so Django auto-computed a hash-based index name at migration-check time that didn't match the human-readable name manually written into the hand-crafted `0001_initial.py`. Fixed by giving the index an explicit name in the model itself, matching the migration — the same root-cause shape as Sprint 2's Meta-options drift, this time for `indexes` instead of `permissions`.
- **Latent permission cross-matching bug in `seed_role_permissions`.** The permission lookup used independent `app_label__in`/`codename__in` filters — a cross-product, not exact `(app_label, codename)` pairs — which only ever worked by coincidence because no codename collided across apps. Rebuilt as a proper OR-of-exact-pairs via `Q` objects now that more apps exist.
- **Stock Adjustment quantity field appeared invisible/unstyled** ("only after clicking the empty area can values be entered"). Root cause: the project's shared `input` styling rule in `static/css/app.css` never included `input[type="number"]` — a pre-existing gap from Sprint 1 that Sprint 2's Drug price fields also silently had. Fixed globally in the one shared rule, so every numeric field in the project is fixed at once, not just this form.
- **Damage/Expired/Lost adjustments increased stock instead of decreasing it.** `StockAdjustment.quantity` is stored as a signed value, but the form exposed that raw signed field directly with nothing enforcing or clarifying the sign convention, so a plain positive entry for "Damage" was taken literally as an increase. Fixed by splitting the input into an explicit Direction (Increase/Decrease) choice plus a magnitude-only Quantity; the ledger's stored semantics are unchanged, only how a person enters the number.
- **Clear Cart button, and both Receipt Print buttons, did nothing.** All three were a `<button>` nested inside another `<button>` — invalid HTML that causes browsers to auto-close the outer element (which carried the actual `hx-post`/`onclick` behavior) when the parser hits the inner one, leaving a non-functional inner button as the only clickable element. Same bug class as the Sprint 2 Filter button fix. Fixed by rendering these three buttons directly instead of wrapping the shared `_button.html` component; **confirmed via a project-wide scan that zero nested-button instances remain anywhere in the codebase.**
- **Quantity spinner incremented by 0.1 instead of 1** on POS and cart quantity fields. Root cause: `step="0.01"` on the number inputs. Fixed to `step="any"` (HTML5-standard: permits any decimal value for typed input — needed for fractional-unit items like liquids — while the native up/down spinner defaults to whole-unit steps).

### Known Limitations

- Same Sprint 2 limitations still apply where unaffected by this sprint (hard-delete on lookup tables, no barcode imaging).
- POS search covers name/generic name/brand name/SKU/barcode only — not Category (that's the Drug list's own filter dropdown, a separate feature).
- No PDF export or WeasyPrint integration for receipts yet — on-screen + browser-print (Thermal/A4 stylesheets) only. No generic Invoice/Purchase Order rendering engine (the "Documents" app) — Purchase Orders can't be built sensibly before Purchases exists anyway.
- "Today's Sales" is a lightweight daily summary, not the full Reports module (date ranges, PDF export, Profit/Inventory/Expiry reports) — that's Sprint 4 scope.
- No Suppliers or Purchases yet — Stock Adjustments (specifically Opening Stock) remain the only way to seed inventory quantity until Purchases ships.
- Global Search (header) is now honestly disabled rather than silently broken, but isn't implemented — deferred to a future sprint per the original Roadmap.

### Upgrade Notes

```bash
python manage.py migrate
python manage.py seed_role_permissions
```

No destructive schema changes. `seed_role_permissions` remains idempotent and safe to re-run.

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
