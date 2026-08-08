"""
Reports module views — Sprint 6.

Every report page follows the same shape (BaseReportView below):
    filter form -> cleaned filter kwargs -> service-layer queryset
    -> display rows (for components/_table.html) and plain export rows
    (for export_service).

Report pages never query models directly — every queryset comes from
apps/reports/services/* (built in Sprint 5), so a report page and the
Dashboard widget that shows the same number can never drift apart on
what it means. Views stay thin: filtering/formatting only.

Permissions: every view gates on one of the four existing
`reports.view_*_reports` permissions (Sprint 5's ReportAccess marker
model) — no new permissions are introduced, and no role-name checks
appear anywhere below, per the Sprint 6 brief.
"""
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from apps.common.permissions import PharmaFlowPermissionMixin
from apps.settings_app.models import PharmacySettings

from . import export_service
from .forms import ReportFilterForm
from .services import financial_report_service as financial_reports
from .services import inventory_report_service as inventory_reports
from .services import purchase_report_service as purchase_reports
from .services import sales_report_service as sales_reports


# ---------------------------------------------------------------------------
# Shared formatting helpers
# ---------------------------------------------------------------------------

def _badge(label, variant):
    return mark_safe(render_to_string("components/_badge.html", {"label": label, "variant": variant}))


STOCK_HEALTH_VARIANTS = {"active": "success", "inactive": "neutral", "discontinued": "danger"}
PURCHASE_STATUS_VARIANTS = {"draft": "neutral", "ordered": "warning", "received": "success", "cancelled": "danger"}
SALE_STATUS_VARIANTS = {"completed": "success", "cancelled": "danger"}


# ---------------------------------------------------------------------------
# Base report view
# ---------------------------------------------------------------------------

class BaseReportView(PharmaFlowPermissionMixin, TemplateView):
    """
    Base class every report page extends. Subclasses declare:
        permission_required  - one of the four reports.view_* perms
        report_title          - shown as the page heading and PDF title
        report_description    - one-line subheading (optional)
        filter_fields          - list of ReportFilterForm field names this report uses
        export_base_name      - filename stem for CSV/XLSX/PDF exports
        chart_type             - "line" | "bar" | None

    and implement:
        get_table(filters)        -> (headers, display_rows) for the screen
        get_export_rows(filters)  -> (headers, plain_rows) for CSV/XLSX/PDF
                                       (defaults to get_table's own output)
        get_summary(filters)      -> optional list of {"label", "value"} cards
        get_chart(filters)        -> optional {"labels": [...], "data": [...], "label": ...}
    """
    template_name = "reports/report_page.html"
    report_title = ""
    report_description = ""
    filter_fields = ["date_from", "date_to"]
    export_base_name = "report"
    chart_type = None
    paginate_by = 25  # UI Contract: "Every table should support ... Pagination"

    @property
    def currency_symbol(self):
        return PharmacySettings.load().currency_symbol

    def money(self, value):
        return f"{self.currency_symbol}{value:,.2f}"

    def get_filter_form(self):
        return ReportFilterForm(self.request.GET or None, fields_needed=self.filter_fields)

    def get_filters(self, form):
        if not form.is_valid():
            return {}
        return {key: value for key, value in form.cleaned_data.items() if value not in (None, "")}

    def get_table(self, filters):
        raise NotImplementedError

    def get_export_rows(self, filters):
        return self.get_table(filters)

    def get_summary(self, filters):
        return None

    def get_chart(self, filters):
        return None

    def get(self, request, *args, **kwargs):
        form = self.get_filter_form()
        filters = self.get_filters(form)
        export_format = request.GET.get("export")
        if export_format in export_service.SUPPORTED_FORMATS:
            headers, rows = self.get_export_rows(filters)
            return export_service.export_response(
                export_format=export_format,
                base_name=self.export_base_name,
                title=self.report_title,
                headers=headers,
                rows=rows,
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        filters = self.get_filters(form)
        headers, rows = self.get_table(filters)

        page_obj = None
        if self.paginate_by:
            paginator = Paginator(rows, self.paginate_by)
            page_obj = paginator.get_page(self.request.GET.get("page"))
            rows = page_obj.object_list

        # Export links carry the same filters currently applied on screen
        # (minus `page`/`export` themselves) so "export what I'm looking
        # at" behaves as expected rather than exporting an unfiltered set.
        base_params = self.request.GET.copy()
        base_params.pop("page", None)
        base_params.pop("export", None)
        export_urls = {}
        for fmt in export_service.SUPPORTED_FORMATS:
            params = base_params.copy()
            params["export"] = fmt
            export_urls[fmt] = f"{self.request.path}?{params.urlencode()}"

        context.update({
            "report_title": self.report_title,
            "report_description": self.report_description,
            "filter_form": form,
            "table_headers": headers,
            "table_rows": rows,
            "page_obj": page_obj,
            "summary_cards": self.get_summary(filters),
            "chart": self.get_chart(filters),
            "chart_type": self.chart_type,
            "querystring": base_params.urlencode(),
            "export_urls": export_urls,
        })
        return context


# ---------------------------------------------------------------------------
# Reports Home — replaces the sidebar's "Reports (Coming Soon)" placeholder
# ---------------------------------------------------------------------------

class ReportsHomeView(PharmaFlowPermissionMixin, TemplateView):
    """
    Landing page linking to every report page the current user is
    permitted to see. Requires at least one reports.* permission — the
    same module-level check the old sidebar placeholder used
    (`perms.reports`) — individual report links are additionally hidden
    per-category in the template via each specific permission, so this
    page never advertises a report the user can't actually open.
    """
    template_name = "reports/report_home.html"
    permission_required = ()  # module-level check only; see has_permission() below

    def has_permission(self):
        return any([
            self.request.user.has_perm("reports.view_inventory_reports"),
            self.request.user.has_perm("reports.view_sales_reports"),
            self.request.user.has_perm("reports.view_purchase_reports"),
            self.request.user.has_perm("reports.view_financial_reports"),
        ])


# ---------------------------------------------------------------------------
# Inventory Reports
# ---------------------------------------------------------------------------

class CurrentStockReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Current Stock"
    report_description = "Full drug catalog with current stock on hand."
    filter_fields = ["category", "drug"]
    export_base_name = "current_stock"

    def get_table(self, filters):
        qs = inventory_reports.current_inventory(category=filters.get("category"))
        if filters.get("drug"):
            qs = qs.filter(pk=filters["drug"].pk)
        headers = ["Drug", "Category", "Unit", "Cost Price", "Selling Price", "Current Stock", "Reorder Level", "Status"]
        rows = [
            [
                d.name, d.category.name, d.unit.name,
                self.money(d.cost_price), self.money(d.selling_price),
                d.current_stock, d.reorder_level,
                _badge(d.get_status_display(), STOCK_HEALTH_VARIANTS.get(d.status, "neutral")),
            ]
            for d in qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        qs = inventory_reports.current_inventory(category=filters.get("category"))
        if filters.get("drug"):
            qs = qs.filter(pk=filters["drug"].pk)
        headers = ["Drug", "Category", "Unit", "Cost Price", "Selling Price", "Current Stock", "Reorder Level", "Status"]
        rows = [
            [d.name, d.category.name, d.unit.name, d.cost_price, d.selling_price, d.current_stock, d.reorder_level, d.get_status_display()]
            for d in qs
        ]
        return headers, rows


class LowStockReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Low Stock"
    report_description = "Drugs at or below their reorder level."
    filter_fields = ["category"]
    export_base_name = "low_stock"

    def get_table(self, filters):
        qs = inventory_reports.low_stock_drugs(category=filters.get("category"))
        headers = ["Drug", "Category", "Current Stock", "Reorder Level", "Shortfall"]
        rows = [[d.name, d.category.name, d.current_stock, d.reorder_level, d.reorder_level - d.current_stock] for d in qs]
        return headers, rows


class ExpiredStockReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Expired Stock"
    report_description = "Drugs on hand with at least one received batch already past its expiry date."
    filter_fields = []
    export_base_name = "expired_stock"

    def get_table(self, filters):
        qs = inventory_reports.expired_drugs()
        headers = ["Drug", "Category", "Current Stock", "Unit"]
        rows = [[d.name, d.category.name, d.current_stock, d.unit.name] for d in qs]
        return headers, rows


class NearExpiryReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Near Expiry"
    report_description = "Drugs on hand with a received batch expiring within the selected window."
    filter_fields = ["days"]
    export_base_name = "near_expiry"

    def get_table(self, filters):
        days = filters.get("days") or 30
        qs = inventory_reports.near_expiry_drugs(days=days)
        headers = ["Drug", "Category", "Current Stock", "Unit"]
        rows = [[d.name, d.category.name, d.current_stock, d.unit.name] for d in qs]
        return headers, rows

    def get_summary(self, filters):
        days = filters.get("days") or 30
        return [{"label": "Expiry Window", "value": f"{days} days"}]


class StockAdjustmentReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Stock Adjustments"
    report_description = "Every inventory correction, with the required reason."
    filter_fields = ["drug", "adjustment_type", "date_from", "date_to"]
    export_base_name = "stock_adjustments"

    def get_table(self, filters):
        qs = inventory_reports.stock_adjustment_report(
            drug=filters.get("drug"), adjustment_type=filters.get("adjustment_type"),
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
        )
        headers = ["Date", "Drug", "Type", "Quantity", "Reason", "Recorded By"]
        rows = [
            [
                a.created_at.strftime("%Y-%m-%d %H:%M"), a.drug.name, a.get_adjustment_type_display(),
                a.quantity, a.reason, a.recorded_by.get_full_name() if a.recorded_by else "—",
            ]
            for a in qs
        ]
        return headers, rows


class InventoryMovementReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Inventory Movements"
    report_description = "The full stock ledger — every increase and decrease, append-only."
    filter_fields = ["drug", "movement_type", "date_from", "date_to"]
    export_base_name = "inventory_movements"

    def get_table(self, filters):
        qs = inventory_reports.movement_report(
            drug=filters.get("drug"), movement_type=filters.get("movement_type"),
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
        )
        headers = ["Date", "Drug", "Type", "Quantity", "Reference", "User"]
        rows = [
            [
                m.created_at.strftime("%Y-%m-%d %H:%M"), m.drug.name, m.get_movement_type_display(),
                m.quantity, m.reference or "—", m.user.get_full_name() if m.user else "—",
            ]
            for m in qs
        ]
        return headers, rows


class InventoryValuationReportView(BaseReportView):
    permission_required = "reports.view_inventory_reports"
    report_title = "Inventory Valuation"
    report_description = "Current stock value, cost and retail, broken down by category."
    filter_fields = []
    export_base_name = "inventory_valuation"

    def get_table(self, filters):
        rows_qs = list(inventory_reports.inventory_valuation_by_category())
        headers = ["Category", "Drugs", "Quantity", "Cost Value", "Retail Value"]
        rows = [
            [
                row["category__name"] or "Uncategorized", row["drug_count"], row["total_quantity"],
                self.money(row["total_cost_value"]), self.money(row["total_retail_value"]),
            ]
            for row in rows_qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(inventory_reports.inventory_valuation_by_category())
        headers = ["Category", "Drugs", "Quantity", "Cost Value", "Retail Value"]
        rows = [
            [row["category__name"] or "Uncategorized", row["drug_count"], row["total_quantity"], row["total_cost_value"], row["total_retail_value"]]
            for row in rows_qs
        ]
        return headers, rows

    def get_summary(self, filters):
        totals = inventory_reports.inventory_valuation()
        return [
            {"label": "Total Drugs", "value": totals["drug_count"]},
            {"label": "Total Quantity", "value": f"{totals['total_quantity']:,.0f}"},
            {"label": "Total Cost Value", "value": self.money(totals["total_cost_value"])},
            {"label": "Total Retail Value", "value": self.money(totals["total_retail_value"])},
        ]


# ---------------------------------------------------------------------------
# Sales Reports
# ---------------------------------------------------------------------------

class SalesPeriodReportView(BaseReportView):
    """
    Backs Daily / Weekly / Monthly Sales — one implementation
    parameterized by `period`, matching sales_report_service.sales_trend's
    own "one function, parameterized" shape rather than three near-
    identical view classes.
    """
    permission_required = "reports.view_sales_reports"
    filter_fields = ["date_from", "date_to"]
    period = "daily"
    chart_type = "line"

    def get_table(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=self.period, date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            user=self.request.user,
        ))
        headers = ["Period", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=self.period, date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            user=self.request.user,
        ))
        headers = ["Period", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], row["revenue"]] for row in rows_qs]
        return headers, rows

    def get_summary(self, filters):
        summary = sales_reports.sales_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        )
        return [
            {"label": "Transactions", "value": summary["count"]},
            {"label": "Revenue", "value": self.money(summary["revenue"])},
            {"label": "Discount Given", "value": self.money(summary["discount_given"])},
        ]

    def get_chart(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=self.period, date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            user=self.request.user,
        ))
        return {
            "labels": [str(row["period"]) for row in rows_qs],
            "data": [float(row["revenue"]) for row in rows_qs],
            "label": "Revenue",
        }


class DailySalesReportView(SalesPeriodReportView):
    period = "daily"
    report_title = "Daily Sales"
    report_description = "Revenue and transaction count, grouped by day."
    export_base_name = "daily_sales"


class WeeklySalesReportView(SalesPeriodReportView):
    period = "weekly"
    report_title = "Weekly Sales"
    report_description = "Revenue and transaction count, grouped by week."
    export_base_name = "weekly_sales"


class MonthlySalesReportView(SalesPeriodReportView):
    period = "monthly"
    report_title = "Monthly Sales"
    report_description = "Revenue and transaction count, grouped by month."
    export_base_name = "monthly_sales"


class SalesDateRangeReportView(BaseReportView):
    permission_required = "reports.view_sales_reports"
    report_title = "Sales — Date Range"
    report_description = "Every individual sale within the selected range."
    filter_fields = ["date_from", "date_to", "cashier", "customer", "payment_method"]
    export_base_name = "sales_date_range"

    def _queryset(self, filters):
        qs = sales_reports.sales_queryset(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            cashier=filters.get("cashier"), customer=filters.get("customer"),
            user=self.request.user,
        )
        if filters.get("payment_method"):
            qs = qs.filter(payment_method=filters["payment_method"])
        return qs

    def get_table(self, filters):
        qs = self._queryset(filters)
        headers = ["Receipt #", "Date", "Customer", "Cashier", "Payment Method", "Discount", "Total", "Status"]
        rows = [
            [
                s.receipt_number, s.created_at.strftime("%Y-%m-%d %H:%M"),
                s.customer.name if s.customer else "Walk-in", s.cashier.get_full_name(),
                s.get_payment_method_display(), self.money(s.discount), self.money(s.total),
                _badge(s.get_status_display(), SALE_STATUS_VARIANTS.get(s.status, "neutral")),
            ]
            for s in qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        qs = self._queryset(filters)
        headers = ["Receipt #", "Date", "Customer", "Cashier", "Payment Method", "Discount", "Total", "Status"]
        rows = [
            [
                s.receipt_number, s.created_at.strftime("%Y-%m-%d %H:%M"),
                s.customer.name if s.customer else "Walk-in", s.cashier.get_full_name(),
                s.get_payment_method_display(), s.discount, s.total, s.get_status_display(),
            ]
            for s in qs
        ]
        return headers, rows

    def get_summary(self, filters):
        summary = sales_reports.sales_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            cashier=filters.get("cashier"), customer=filters.get("customer"), user=self.request.user,
        )
        return [
            {"label": "Transactions", "value": summary["count"]},
            {"label": "Revenue", "value": self.money(summary["revenue"])},
        ]


class SalesByDrugReportView(BaseReportView):
    permission_required = "reports.view_sales_reports"
    report_title = "Sales by Drug"
    report_description = "Units sold and revenue generated, per drug."
    filter_fields = ["date_from", "date_to"]
    export_base_name = "sales_by_drug"
    chart_type = "bar"

    def get_table(self, filters):
        rows_qs = list(sales_reports.sales_by_drug(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Drug", "Quantity Sold", "Revenue"]
        rows = [[row["drug__name"], row["quantity"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.sales_by_drug(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Drug", "Quantity Sold", "Revenue"]
        rows = [[row["drug__name"], row["quantity"], row["revenue"]] for row in rows_qs]
        return headers, rows

    def get_chart(self, filters):
        rows_qs = list(sales_reports.sales_by_drug(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user, limit=10,
        ))
        return {"labels": [r["drug__name"] for r in rows_qs], "data": [float(r["revenue"]) for r in rows_qs], "label": "Revenue"}


class SalesByCustomerReportView(BaseReportView):
    permission_required = "reports.view_sales_reports"
    report_title = "Sales by Customer"
    report_description = "Transactions and revenue per customer. Walk-in sales are grouped together."
    filter_fields = ["date_from", "date_to"]
    export_base_name = "sales_by_customer"

    def get_table(self, filters):
        rows_qs = list(sales_reports.sales_by_customer(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Customer", "Transactions", "Revenue"]
        rows = [[row["customer__name"] or "Walk-in", row["count"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.sales_by_customer(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Customer", "Transactions", "Revenue"]
        rows = [[row["customer__name"] or "Walk-in", row["count"], row["revenue"]] for row in rows_qs]
        return headers, rows


class SalesByCashierReportView(BaseReportView):
    permission_required = "reports.view_sales_reports"
    report_title = "Sales by Cashier"
    report_description = "Transactions and revenue per cashier."
    filter_fields = ["date_from", "date_to"]
    export_base_name = "sales_by_cashier"

    def get_table(self, filters):
        rows_qs = list(sales_reports.sales_by_cashier(date_from=filters.get("date_from"), date_to=filters.get("date_to")))
        headers = ["Cashier", "Transactions", "Revenue"]
        rows = [
            [(f"{row['cashier__first_name']} {row['cashier__last_name']}".strip() or row["cashier__username"]), row["count"], self.money(row["revenue"])]
            for row in rows_qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.sales_by_cashier(date_from=filters.get("date_from"), date_to=filters.get("date_to")))
        headers = ["Cashier", "Transactions", "Revenue"]
        rows = [
            [(f"{row['cashier__first_name']} {row['cashier__last_name']}".strip() or row["cashier__username"]), row["count"], row["revenue"]]
            for row in rows_qs
        ]
        return headers, rows


class PaymentMethodSummaryReportView(BaseReportView):
    permission_required = "reports.view_sales_reports"
    report_title = "Payment Method Summary"
    report_description = "Revenue split by how customers paid."
    filter_fields = ["date_from", "date_to"]
    export_base_name = "payment_method_summary"
    chart_type = "bar"

    def get_table(self, filters):
        rows_qs = list(sales_reports.payment_method_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Payment Method", "Transactions", "Revenue"]
        rows = [[row["payment_method"].replace("_", " ").title(), row["count"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.payment_method_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Payment Method", "Transactions", "Revenue"]
        rows = [[row["payment_method"].replace("_", " ").title(), row["count"], row["revenue"]] for row in rows_qs]
        return headers, rows

    def get_chart(self, filters):
        rows_qs = list(sales_reports.payment_method_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        ))
        return {
            "labels": [r["payment_method"].replace("_", " ").title() for r in rows_qs],
            "data": [float(r["revenue"]) for r in rows_qs],
            "label": "Revenue",
        }


# ---------------------------------------------------------------------------
# Purchase Reports
# ---------------------------------------------------------------------------

class PurchaseHistoryReportView(BaseReportView):
    permission_required = "reports.view_purchase_reports"
    report_title = "Purchase History"
    report_description = "Every purchase order, across every lifecycle status."
    filter_fields = ["date_from", "date_to", "supplier", "purchase_status"]
    export_base_name = "purchase_history"

    def _queryset(self, filters):
        return purchase_reports.purchase_queryset(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            supplier=filters.get("supplier"), status=filters.get("purchase_status"),
        )

    def get_table(self, filters):
        qs = self._queryset(filters)
        headers = ["Purchase #", "Supplier", "Date", "Grand Total", "Status"]
        rows = [
            [p.purchase_number, p.supplier.company_name, p.purchase_date, self.money(p.grand_total),
             _badge(p.get_status_display(), PURCHASE_STATUS_VARIANTS.get(p.status, "neutral"))]
            for p in qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        qs = self._queryset(filters)
        headers = ["Purchase #", "Supplier", "Date", "Grand Total", "Status"]
        rows = [[p.purchase_number, p.supplier.company_name, p.purchase_date, p.grand_total, p.get_status_display()] for p in qs]
        return headers, rows

    def get_summary(self, filters):
        summary = purchase_reports.purchase_summary(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"),
            supplier=filters.get("supplier"), status=filters.get("purchase_status"),
        )
        return [
            {"label": "Orders", "value": summary["count"]},
            {"label": "Total Cost", "value": self.money(summary["total_cost"])},
        ]


class PurchasesBySupplierReportView(BaseReportView):
    permission_required = "reports.view_purchase_reports"
    report_title = "Purchases by Supplier"
    report_description = "Order count and total cost per supplier."
    filter_fields = ["date_from", "date_to", "purchase_status"]
    export_base_name = "purchases_by_supplier"
    chart_type = "bar"

    def get_table(self, filters):
        rows_qs = list(purchase_reports.purchases_by_supplier(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), status=filters.get("purchase_status"),
        ))
        headers = ["Supplier", "Orders", "Total Cost"]
        rows = [[row["supplier__company_name"], row["order_count"], self.money(row["total_cost"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(purchase_reports.purchases_by_supplier(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), status=filters.get("purchase_status"),
        ))
        headers = ["Supplier", "Orders", "Total Cost"]
        rows = [[row["supplier__company_name"], row["order_count"], row["total_cost"]] for row in rows_qs]
        return headers, rows

    def get_chart(self, filters):
        rows_qs = list(purchase_reports.purchases_by_supplier(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), status=filters.get("purchase_status"),
        ))[:10]
        return {"labels": [r["supplier__company_name"] for r in rows_qs], "data": [float(r["total_cost"]) for r in rows_qs], "label": "Total Cost"}


class PurchasesByDrugReportView(BaseReportView):
    permission_required = "reports.view_purchase_reports"
    report_title = "Purchases by Drug"
    report_description = "Quantity received and total cost per drug (received orders only)."
    filter_fields = ["date_from", "date_to"]
    export_base_name = "purchases_by_drug"

    def get_table(self, filters):
        rows_qs = list(purchase_reports.purchases_by_drug(date_from=filters.get("date_from"), date_to=filters.get("date_to")))
        headers = ["Drug", "Quantity Received", "Total Cost"]
        rows = [[row["drug__name"], row["quantity"], self.money(row["total_cost"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(purchase_reports.purchases_by_drug(date_from=filters.get("date_from"), date_to=filters.get("date_to")))
        headers = ["Drug", "Quantity Received", "Total Cost"]
        rows = [[row["drug__name"], row["quantity"], row["total_cost"]] for row in rows_qs]
        return headers, rows


class PurchaseCostAnalysisReportView(BaseReportView):
    permission_required = "reports.view_purchase_reports"
    report_title = "Purchase Cost Analysis"
    report_description = "Received purchase cost over time."
    filter_fields = ["date_from", "date_to", "period"]
    export_base_name = "purchase_cost_analysis"
    chart_type = "line"

    def get_table(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        headers = ["Period", "Orders", "Total Cost"]
        rows = [[row["period"], row["count"], self.money(row["total_cost"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        headers = ["Period", "Orders", "Total Cost"]
        rows = [[row["period"], row["count"], row["total_cost"]] for row in rows_qs]
        return headers, rows

    def get_chart(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        return {"labels": [str(r["period"]) for r in rows_qs], "data": [float(r["total_cost"]) for r in rows_qs], "label": "Purchase Cost"}


class OutstandingPurchaseOrdersReportView(BaseReportView):
    permission_required = "reports.view_purchase_reports"
    report_title = "Outstanding Purchase Orders"
    report_description = "Draft and Ordered purchase orders not yet received."
    filter_fields = ["supplier"]
    export_base_name = "outstanding_purchase_orders"

    def get_table(self, filters):
        qs = purchase_reports.outstanding_draft_orders(supplier=filters.get("supplier"))
        headers = ["Purchase #", "Supplier", "Date", "Grand Total", "Status"]
        rows = [
            [p.purchase_number, p.supplier.company_name, p.purchase_date, self.money(p.grand_total),
             _badge(p.get_status_display(), PURCHASE_STATUS_VARIANTS.get(p.status, "neutral"))]
            for p in qs
        ]
        return headers, rows

    def get_export_rows(self, filters):
        qs = purchase_reports.outstanding_draft_orders(supplier=filters.get("supplier"))
        headers = ["Purchase #", "Supplier", "Date", "Grand Total", "Status"]
        rows = [[p.purchase_number, p.supplier.company_name, p.purchase_date, p.grand_total, p.get_status_display()] for p in qs]
        return headers, rows


# ---------------------------------------------------------------------------
# Financial Reports
# ---------------------------------------------------------------------------

class RevenueReportView(BaseReportView):
    permission_required = "reports.view_financial_reports"
    report_title = "Revenue"
    report_description = "Sales revenue over time."
    filter_fields = ["date_from", "date_to", "period"]
    export_base_name = "revenue"
    chart_type = "line"

    def get_table(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Period", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), user=self.request.user,
        ))
        headers = ["Period", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], row["revenue"]] for row in rows_qs]
        return headers, rows

    def get_summary(self, filters):
        total = financial_reports.revenue(date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user)
        return [{"label": "Total Revenue", "value": self.money(total)}]

    def get_chart(self, filters):
        rows_qs = list(sales_reports.sales_trend(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), user=self.request.user,
        ))
        return {"labels": [str(r["period"]) for r in rows_qs], "data": [float(r["revenue"]) for r in rows_qs], "label": "Revenue"}


class PurchaseCostReportView(BaseReportView):
    permission_required = "reports.view_financial_reports"
    report_title = "Purchase Cost"
    report_description = "Received purchase cost over time — only Received orders count as actual cost incurred."
    filter_fields = ["date_from", "date_to", "period"]
    export_base_name = "purchase_cost"
    chart_type = "line"

    def get_table(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        headers = ["Period", "Orders", "Total Cost"]
        rows = [[row["period"], row["count"], self.money(row["total_cost"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        headers = ["Period", "Orders", "Total Cost"]
        rows = [[row["period"], row["count"], row["total_cost"]] for row in rows_qs]
        return headers, rows

    def get_summary(self, filters):
        total = financial_reports.purchase_cost(date_from=filters.get("date_from"), date_to=filters.get("date_to"))
        return [{"label": "Total Purchase Cost", "value": self.money(total)}]

    def get_chart(self, filters):
        from apps.purchases.models import STATUS_RECEIVED
        rows_qs = list(purchase_reports.purchases_by_date(
            period=filters.get("period") or "daily", date_from=filters.get("date_from"),
            date_to=filters.get("date_to"), status=STATUS_RECEIVED,
        ))
        return {"labels": [str(r["period"]) for r in rows_qs], "data": [float(r["total_cost"]) for r in rows_qs], "label": "Purchase Cost"}


class EstimatedGrossProfitReportView(BaseReportView):
    permission_required = "reports.view_financial_reports"
    report_title = "Estimated Gross Profit"
    report_description = (
        "Revenue minus estimated cost of goods sold (each drug's current cost price x quantity sold). "
        "An estimate, not a statutory profit figure — PharmaFlow does not yet track per-sale cost history "
        "(see Future Enhancements Backlog PFE-010)."
    )
    filter_fields = ["date_from", "date_to"]
    export_base_name = "estimated_gross_profit"

    def get_table(self, filters):
        result = financial_reports.estimated_gross_profit(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        )
        headers = ["Metric", "Amount"]
        rows = [
            ["Revenue", self.money(result["revenue"])],
            ["Estimated Cost of Goods Sold", self.money(result["estimated_cogs"])],
            ["Estimated Gross Profit", self.money(result["estimated_gross_profit"])],
        ]
        return headers, rows

    def get_export_rows(self, filters):
        result = financial_reports.estimated_gross_profit(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        )
        headers = ["Metric", "Amount"]
        rows = [
            ["Revenue", result["revenue"]],
            ["Estimated Cost of Goods Sold", result["estimated_cogs"]],
            ["Estimated Gross Profit", result["estimated_gross_profit"]],
        ]
        return headers, rows

    def get_summary(self, filters):
        result = financial_reports.estimated_gross_profit(
            date_from=filters.get("date_from"), date_to=filters.get("date_to"), user=self.request.user,
        )
        margin = (result["estimated_gross_profit"] / result["revenue"] * 100) if result["revenue"] else 0
        return [
            {"label": "Revenue", "value": self.money(result["revenue"])},
            {"label": "Estimated COGS", "value": self.money(result["estimated_cogs"])},
            {"label": "Estimated Gross Profit", "value": self.money(result["estimated_gross_profit"])},
            {"label": "Estimated Margin", "value": f"{margin:.1f}%"},
        ]


class InventoryValueReportView(BaseReportView):
    permission_required = "reports.view_financial_reports"
    report_title = "Inventory Value"
    report_description = "Current stock value at cost. See the Inventory Valuation report for a category breakdown."
    filter_fields = []
    export_base_name = "inventory_value"

    def get_table(self, filters):
        totals = inventory_reports.inventory_valuation()
        headers = ["Metric", "Value"]
        rows = [
            ["Total Drugs", totals["drug_count"]],
            ["Total Quantity", f"{totals['total_quantity']:,.0f}"],
            ["Total Cost Value", self.money(totals["total_cost_value"])],
            ["Total Retail Value", self.money(totals["total_retail_value"])],
        ]
        return headers, rows

    def get_export_rows(self, filters):
        totals = inventory_reports.inventory_valuation()
        headers = ["Metric", "Value"]
        rows = [
            ["Total Drugs", totals["drug_count"]],
            ["Total Quantity", totals["total_quantity"]],
            ["Total Cost Value", totals["total_cost_value"]],
            ["Total Retail Value", totals["total_retail_value"]],
        ]
        return headers, rows

    def get_summary(self, filters):
        value = financial_reports.inventory_value()
        return [{"label": "Inventory Value (Cost)", "value": self.money(value)}]


class AverageDailySalesReportView(BaseReportView):
    permission_required = "reports.view_financial_reports"
    report_title = "Average Daily Sales"
    report_description = "Average daily revenue over the selected trailing window."
    filter_fields = ["days"]
    export_base_name = "average_daily_sales"
    chart_type = "line"

    def get_table(self, filters):
        days = filters.get("days") or 30
        rows_qs = list(sales_reports.sales_trend(period="daily", user=self.request.user))[-days:]
        headers = ["Date", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], self.money(row["revenue"])] for row in rows_qs]
        return headers, rows

    def get_export_rows(self, filters):
        days = filters.get("days") or 30
        rows_qs = list(sales_reports.sales_trend(period="daily", user=self.request.user))[-days:]
        headers = ["Date", "Transactions", "Revenue"]
        rows = [[row["period"], row["count"], row["revenue"]] for row in rows_qs]
        return headers, rows

    def get_summary(self, filters):
        days = filters.get("days") or 30
        average = financial_reports.average_daily_sales(days=days, user=self.request.user)
        return [{"label": f"Average Daily Sales ({days} days)", "value": self.money(average)}]

    def get_chart(self, filters):
        days = filters.get("days") or 30
        rows_qs = list(sales_reports.sales_trend(period="daily", user=self.request.user))[-days:]
        return {"labels": [str(r["period"]) for r in rows_qs], "data": [float(r["revenue"]) for r in rows_qs], "label": "Revenue"}
