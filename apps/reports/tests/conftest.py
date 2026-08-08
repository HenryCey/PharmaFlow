"""
Sprint 6 — shared fixture for apps/reports/tests/.

`seeded_pharmacy` here is the same fixture test_services.py already
defines locally (Sprint 5). It's duplicated into conftest.py rather than
extracted out of test_services.py and imported, so that file — already
passing, already reviewed — is left completely untouched per the project
rule "do not redesign completed modules". test_views.py below picks this
fixture up automatically from conftest.py; a same-named local fixture in
any test module (like test_services.py's own) simply takes precedence
for that module, so there's no conflict either way.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.customers.models import Customer
from apps.inventory.models import Category, Drug, Unit
from apps.purchases.models import PurchaseItem, PurchaseOrder, STATUS_DRAFT
from apps.purchases.receiving_service import receive_purchase
from apps.sales.models import PAYMENT_CASH, Sale, SaleItem
from apps.settings_app.services import generate_document_number
from apps.stock.models import MOVEMENT_SALE
from apps.stock.services import record_movement
from apps.suppliers.models import Supplier


@pytest.fixture
def seeded_pharmacy(db):
    from django.core.management import call_command

    call_command("seed_role_permissions")

    owner = User.objects.create_user(
        username="owner1", password="testpass123",
        role=Role.objects.get(name="Owner"),
    )
    cashier = User.objects.create_user(
        username="cashier1", password="testpass123",
        role=Role.objects.get(name="Cashier"),
    )
    pharmacist = User.objects.create_user(
        username="pharmacist1", password="testpass123",
        role=Role.objects.get(name="Pharmacist"),
    )

    category = Category.objects.create(name="Analgesics")
    unit = Unit.objects.create(name="Tablet")
    paracetamol = Drug.objects.create(
        name="Paracetamol 500mg", category=category, unit=unit,
        cost_price=Decimal("50"), selling_price=Decimal("100"),
        reorder_level=Decimal("20"), created_by=owner,
    )
    amoxicillin = Drug.objects.create(
        name="Amoxicillin 250mg", category=category, unit=unit,
        cost_price=Decimal("150"), selling_price=Decimal("300"),
        reorder_level=Decimal("10"), created_by=owner,
    )
    vitamin_c = Drug.objects.create(
        name="Vitamin C 1000mg", category=category, unit=unit,
        cost_price=Decimal("80"), selling_price=Decimal("150"),
        reorder_level=Decimal("5"), created_by=owner,
    )

    supplier = Supplier.objects.create(
        supplier_code=generate_document_number("supplier_code"),
        company_name="MedSupply Ltd", phone="08000000000", created_by=owner,
    )

    today = timezone.localdate()
    po = PurchaseOrder.objects.create(
        purchase_number=generate_document_number("purchase_order"),
        supplier=supplier, purchase_date=today, status=STATUS_DRAFT,
        created_by=owner, subtotal=Decimal("25400"), grand_total=Decimal("25400"),
    )
    PurchaseItem.objects.create(
        purchase=po, drug=paracetamol, quantity=Decimal("200"), unit_cost=Decimal("50"),
        selling_price=Decimal("100"), expiry_date=today + timedelta(days=20),
        subtotal=Decimal("10000"),
    )
    PurchaseItem.objects.create(
        purchase=po, drug=amoxicillin, quantity=Decimal("100"), unit_cost=Decimal("150"),
        selling_price=Decimal("300"), expiry_date=today + timedelta(days=400),
        subtotal=Decimal("15000"),
    )
    PurchaseItem.objects.create(
        purchase=po, drug=vitamin_c, quantity=Decimal("5"), unit_cost=Decimal("80"),
        selling_price=Decimal("150"), expiry_date=today + timedelta(days=400),
        subtotal=Decimal("400"),
    )
    receive_purchase(purchase=po, user=owner)

    customer = Customer.objects.create(name="Jane Doe", phone="08011111111")

    for i in range(5):
        receipt = generate_document_number("sale_receipt")
        sale = Sale.objects.create(
            receipt_number=receipt,
            customer=customer if i % 2 == 0 else None,
            cashier=cashier, payment_method=PAYMENT_CASH, total=Decimal("300"),
        )
        SaleItem.objects.create(sale=sale, drug=paracetamol, quantity=Decimal("2"), unit_price=Decimal("100"))
        SaleItem.objects.create(sale=sale, drug=amoxicillin, quantity=Decimal("1"), unit_price=Decimal("300"))
        record_movement(drug=paracetamol, movement_type=MOVEMENT_SALE, quantity=Decimal("-2"), user=cashier, reference=receipt)
        record_movement(drug=amoxicillin, movement_type=MOVEMENT_SALE, quantity=Decimal("-1"), user=cashier, reference=receipt)

    return {
        "owner": owner, "cashier": cashier, "pharmacist": pharmacist,
        "customer": customer, "supplier": supplier,
        "paracetamol": paracetamol, "amoxicillin": amoxicillin, "vitamin_c": vitamin_c,
        "purchase_order": po,
    }
