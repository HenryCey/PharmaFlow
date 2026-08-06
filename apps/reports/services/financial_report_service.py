"""
Financial summary — Sprint 5 (Feature Specs: "Financial Summary").

Deliberately thin: every figure here is composed from
sales_report_service / purchase_report_service / inventory_report_service
rather than querying Sale/PurchaseOrder/Drug directly, so there is
exactly one implementation of "what counts as revenue" etc. anywhere in
the project.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.purchases.models import STATUS_RECEIVED
from apps.sales.models import SaleItem

from . import inventory_report_service as inventory_reports
from . import purchase_report_service as purchase_reports
from . import sales_report_service as sales_reports


def revenue(*, date_from=None, date_to=None, user=None):
    return sales_reports.sales_summary(date_from=date_from, date_to=date_to, user=user)["revenue"]


def purchase_cost(*, date_from=None, date_to=None):
    """Only Received purchase orders count as actual cost incurred —
    a Draft/Ordered order hasn't been paid for or entered stock yet."""
    return purchase_reports.purchase_summary(
        date_from=date_from, date_to=date_to, status=STATUS_RECEIVED
    )["total_cost"]


def estimated_gross_profit(*, date_from=None, date_to=None, user=None):
    """
    Deliberately named 'estimated' (matching the Sprint 5 brief's own
    wording). SaleItem.unit_price is a *selling*-price snapshot only —
    the project has no per-sale cost snapshot, and the documented
    costing policy is Last Cost Wins, not FIFO/weighted-average/batch
    costing (see FUTURE_ENHANCEMENTS_BACKLOG PFE-010). Cost of goods
    sold is therefore approximated as quantity-sold x each drug's
    *current* cost_price, which will misstate COGS for any period where
    a drug's cost has since changed. This is a trend indicator, not a
    statutory profit figure — flagged here and wherever it's displayed.
    """
    sales = sales_reports.sales_queryset(date_from=date_from, date_to=date_to, user=user)
    rev = sales.aggregate(revenue=Coalesce(Sum("total"), Decimal("0")))["revenue"]
    cogs = SaleItem.objects.filter(sale__in=sales).aggregate(
        cogs=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("quantity") * F("drug__cost_price"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            ),
            Decimal("0"),
        )
    )["cogs"]
    return {
        "revenue": rev,
        "estimated_cogs": cogs,
        "estimated_gross_profit": rev - cogs,
    }


def inventory_value():
    return inventory_reports.inventory_valuation()["total_cost_value"]


def average_daily_sales(*, days=30, user=None):
    """Feature Specs: 'Average Daily Sales'."""
    if days <= 0:
        return Decimal("0")
    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)
    total = revenue(date_from=date_from, date_to=today, user=user)
    return total / days


def financial_summary(*, date_from=None, date_to=None, user=None):
    """Convenience aggregate for the Financial Summary report page and
    the dashboard's financial KPI cards."""
    profit = estimated_gross_profit(date_from=date_from, date_to=date_to, user=user)
    return {
        **profit,
        "purchase_cost": purchase_cost(date_from=date_from, date_to=date_to),
        "inventory_value": inventory_value(),
        "average_daily_sales": average_daily_sales(user=user),
    }
