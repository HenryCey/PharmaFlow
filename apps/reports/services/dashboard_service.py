"""
Dashboard service — Sprint 5.

Per the Sprint 5 brief: "Dashboard cards should obtain their values from
DashboardService." This module owns nothing on its own — every figure is
composed from inventory_report_service / sales_report_service /
purchase_report_service / financial_report_service, so the dashboard and
the future report pages can never drift apart on what a number means.

Sprint 5 refinement round (TESTBUILD v2): every widget below is now
gated on the same Django permission its full report page will eventually
require, and — per the round's Task 6 ("avoid computing datasets for
widgets the user can't see") — the underlying query for a widget is only
ever run when the permission check passes. Nothing about *how* a figure
is calculated changed; report service modules below this one were not
touched.

Permission-to-widget mapping (documented once, here, rather than
scattered across the template):

    sales.view_sale               -> Today's Sales, Recent Sales,
                                      Sales Trend chart, Top Selling Drugs chart
    purchases.view_purchaseorder  -> Today's Purchases, Recent Purchases,
                                      Purchase Trend chart
    inventory.change_drug         -> Inventory Value, Inventory Quantity,
                                      Low Stock, Out-of-Stock, Near Expiry,
                                      Inventory Distribution chart
    customers.view_customer       -> Total Customers
    suppliers.view_supplier       -> Total Suppliers
    stock.view_inventorymovement  -> Recent Inventory Movements
    reports.view_financial_reports -> Estimated Gross Profit

`inventory.change_drug` (not `inventory.view_drug`) is used for the
inventory-value-adjacent cards deliberately: `view_drug` is also granted
to Cashier for POS drug lookup (see seed_role_permissions.py's Cashier
comment), so gating on it would leak inventory valuation/stock-health
figures to a role that should only ever see individual drug names and
prices at the till. `change_drug` is only held by roles that actually
manage inventory (Owner, Administrator, Pharmacist), which is what these
cards are actually about.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.customers.models import Customer
from apps.inventory.models import Drug
from apps.purchases.models import STATUS_RECEIVED as PURCHASE_RECEIVED
from apps.stock.models import InventoryMovement
from apps.suppliers.models import Supplier

from . import financial_report_service as financial_reports
from . import inventory_report_service as inventory_reports
from . import purchase_report_service as purchase_reports
from . import sales_report_service as sales_reports


def kpi_cards(*, user):
    """
    Feature list: Total Sales Today, Total Purchases Today, Current
    Inventory Value/Quantity, Total Customers, Total Suppliers, Low
    Stock, Out-of-Stock, Near Expiry.

    Returns only the keys the user has permission to see — the template
    checks for key *presence* (`{% if "x" in kpis %}`), not truthiness,
    so a legitimate zero value is never mistaken for "not permitted".
    """
    today = timezone.localdate()
    kpis = {}

    if user.has_perm("sales.view_sale"):
        todays_sales = sales_reports.sales_summary(date_from=today, date_to=today, user=user)
        kpis["todays_sales_revenue"] = todays_sales["revenue"]
        kpis["todays_sales_count"] = todays_sales["count"]

    if user.has_perm("purchases.view_purchaseorder"):
        todays_purchases = purchase_reports.purchase_summary(
            date_from=today, date_to=today, status=PURCHASE_RECEIVED
        )
        kpis["todays_purchases_cost"] = todays_purchases["total_cost"]
        kpis["todays_purchases_count"] = todays_purchases["count"]

    if user.has_perm("inventory.change_drug"):
        valuation = inventory_reports.inventory_valuation()
        kpis["inventory_value"] = valuation["total_cost_value"]
        kpis["inventory_quantity"] = valuation["total_quantity"]
        kpis["low_stock_count"] = inventory_reports.low_stock_drugs().count()
        kpis["out_of_stock_count"] = inventory_reports.out_of_stock_drugs().count()
        kpis["near_expiry_count"] = inventory_reports.near_expiry_drugs().count()

    if user.has_perm("customers.view_customer"):
        kpis["total_customers"] = Customer.objects.count()

    if user.has_perm("suppliers.view_supplier"):
        kpis["total_suppliers"] = Supplier.objects.count()

    return kpis


def recent_activity(*, limit=5, user):
    """Feature list: Recent Sales, Recent Purchases, Recent Inventory
    Movements. Same presence-not-truthiness contract as kpi_cards: an
    empty-but-permitted list is still a present key (`[]`), rendered by
    the template's own `{% empty %}` block; a genuinely unpermitted
    widget's key is absent entirely."""
    activity = {}

    if user.has_perm("sales.view_sale"):
        activity["recent_sales"] = list(
            sales_reports.sales_queryset(status=None, user=user)[:limit]
        )

    if user.has_perm("purchases.view_purchaseorder"):
        activity["recent_purchases"] = list(
            purchase_reports.purchase_queryset()[:limit]
        )

    if user.has_perm("stock.view_inventorymovement"):
        activity["recent_movements"] = list(
            InventoryMovement.objects.select_related("drug", "user")[:limit]
        )

    return activity


def sales_trend_chart(*, days=7, user=None):
    """Feature list: 'Sales Trend' chart."""
    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)
    rows = {
        row["period"]: row["revenue"]
        for row in sales_reports.sales_trend(
            period="daily", date_from=date_from, date_to=today, user=user
        )
    }

    labels, data = [], []
    for offset in range(days):
        day = date_from + timedelta(days=offset)
        labels.append(day.strftime("%b %d"))
        data.append(float(rows.get(day, Decimal("0"))))
    return {"labels": labels, "data": data}


def purchase_trend_chart(*, days=7):
    """Feature list: 'Purchase Trend' chart."""
    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)
    rows = {
        row["period"]: row["total_cost"]
        for row in purchase_reports.purchases_by_date(
            period="daily", date_from=date_from, date_to=today, status=PURCHASE_RECEIVED
        )
    }

    labels, data = [], []
    for offset in range(days):
        day = date_from + timedelta(days=offset)
        labels.append(day.strftime("%b %d"))
        data.append(float(rows.get(day, Decimal("0"))))
    return {"labels": labels, "data": data}


def top_selling_drugs_chart(*, limit=5, days=30, user=None):
    """Feature list: 'Top Selling Drugs' chart."""
    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)
    rows = list(
        sales_reports.top_selling_drugs(
            limit=limit, date_from=date_from, date_to=today, user=user
        )
    )
    return {
        "labels": [row["drug__name"] for row in rows],
        "data": [float(row["quantity"]) for row in rows],
    }


def inventory_distribution_chart(*, limit=6):
    """Feature list: 'Inventory Distribution' chart — current stock
    grouped by category."""
    rows = list(
        Drug.objects.filter(current_stock__gt=0)
        .values("category__name")
        .annotate(total=Coalesce(Sum("current_stock"), Decimal("0")))
        .order_by("-total")[:limit]
    )
    return {
        "labels": [row["category__name"] or "Uncategorized" for row in rows],
        "data": [float(row["total"]) for row in rows],
    }


def todays_financials(*, user):
    """Feature list: an at-a-glance profit figure for the dashboard,
    scoped to today. See financial_report_service.estimated_gross_profit
    for why this is explicitly an estimate. Returns None (not a zeroed
    dict) when the user lacks reports.view_financial_reports, so the
    template can tell "not permitted" apart from "zero profit today"."""
    if not user.has_perm("reports.view_financial_reports"):
        return None
    today = timezone.localdate()
    return financial_reports.estimated_gross_profit(date_from=today, date_to=today, user=user)


def dashboard_context(*, user):
    """
    Everything the redesigned Dashboard template needs, in one call —
    scoped to what `user` is permitted to see. Chart data is only
    computed when the KPI/activity gate for the same permission passed,
    so a role with none of the relevant permissions triggers none of the
    underlying report queries (Task 6: avoid unnecessary Dashboard
    queries for widgets that won't render).
    """
    kpis = kpi_cards(user=user)
    activity = recent_activity(user=user)

    context = {
        "kpis": kpis,
        "financial": todays_financials(user=user),
        "activity": activity,
    }

    if "todays_sales_revenue" in kpis:
        context["sales_trend"] = sales_trend_chart(user=user)
        context["top_drugs"] = top_selling_drugs_chart(user=user)

    if "todays_purchases_cost" in kpis:
        context["purchase_trend"] = purchase_trend_chart()

    if "inventory_value" in kpis:
        context["inventory_distribution"] = inventory_distribution_chart()

    return context
