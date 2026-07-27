# PharmaFlow — Sprint 1 (Foundation)

Sprint 1 delivers the roadmap milestone: **users can securely log in and
navigate the application.**

## What's included

- Project scaffold: `config/settings/{base,development,production}.py`
- `apps/common`: `TimeStampedModel`, `SoftDeleteModel`, permission mixin
- `apps/accounts`: custom `User`, `Role` (wraps `auth.Group`), `LoginHistory`,
  login/logout, password change, User CRUD, Role CRUD, default roles
  (Owner, Administrator, Pharmacist, Cashier)
- `apps/settings_app`: `PharmacySettings` (singleton), `NumberingSequence`
  (+ atomic `generate_document_number()` service), single-currency config
  defaulting to ₦
- `apps/dashboard`: placeholder landing page (real KPIs ship in Sprint 4)
- One application shell (`templates/layout/`) and a reusable component
  library (`templates/components/`) per the UI Contract

## Explicitly NOT in Sprint 1

Drug/Inventory, Suppliers, Purchases, Stock Adjustments, Customers, Sales
(POS), Reports, Documents, Notifications logic, Activity Log UI, Global
Search logic, Backup & Restore — these ship in their designated sprints
per the Development Roadmap.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit values for your machine

createdb pharmaflow    # or create the DB another way — Postgres is required
                        # in every deployment mode, including local

python manage.py migrate
python manage.py seed_role_permissions   # run again after future sprints add apps
python manage.py createsuperuser
python manage.py runserver
```

Then log in at `/accounts/login/` with the superuser account, assign it
the **Owner** role from `/accounts/users/` (or Django admin), and use
`/settings/` to set the pharmacy name and currency symbol.

## Sprint 1 exit criteria

A user in each of the four default roles can log in, see a sidebar
restricted to what they're permitted to use, see their name/role in the
header, log out, and change their password — with a `LoginHistory` row
created on every attempt, success or failure.
