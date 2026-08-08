from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportsHomeView.as_view(), name="home"),

    # Inventory Reports
    path("inventory/current-stock/", views.CurrentStockReportView.as_view(), name="current_stock"),
    path("inventory/low-stock/", views.LowStockReportView.as_view(), name="low_stock"),
    path("inventory/near-expiry/", views.NearExpiryReportView.as_view(), name="near_expiry"),
    path("inventory/expired-stock/", views.ExpiredStockReportView.as_view(), name="expired_stock"),
    path("inventory/stock-adjustments/", views.StockAdjustmentReportView.as_view(), name="stock_adjustments"),
    path("inventory/movements/", views.InventoryMovementReportView.as_view(), name="inventory_movements"),
    path("inventory/valuation/", views.InventoryValuationReportView.as_view(), name="inventory_valuation"),

    # Sales Reports
    path("sales/daily/", views.DailySalesReportView.as_view(), name="daily_sales"),
    path("sales/weekly/", views.WeeklySalesReportView.as_view(), name="weekly_sales"),
    path("sales/monthly/", views.MonthlySalesReportView.as_view(), name="monthly_sales"),
    path("sales/date-range/", views.SalesDateRangeReportView.as_view(), name="sales_date_range"),
    path("sales/by-drug/", views.SalesByDrugReportView.as_view(), name="sales_by_drug"),
    path("sales/by-customer/", views.SalesByCustomerReportView.as_view(), name="sales_by_customer"),
    path("sales/by-cashier/", views.SalesByCashierReportView.as_view(), name="sales_by_cashier"),
    path("sales/payment-methods/", views.PaymentMethodSummaryReportView.as_view(), name="payment_method_summary"),

    # Purchase Reports
    path("purchases/history/", views.PurchaseHistoryReportView.as_view(), name="purchase_history"),
    path("purchases/by-supplier/", views.PurchasesBySupplierReportView.as_view(), name="purchases_by_supplier"),
    path("purchases/by-drug/", views.PurchasesByDrugReportView.as_view(), name="purchases_by_drug"),
    path("purchases/cost-analysis/", views.PurchaseCostAnalysisReportView.as_view(), name="purchase_cost_analysis"),
    path("purchases/outstanding/", views.OutstandingPurchaseOrdersReportView.as_view(), name="outstanding_purchase_orders"),

    # Financial Reports
    path("financial/revenue/", views.RevenueReportView.as_view(), name="revenue"),
    path("financial/purchase-cost/", views.PurchaseCostReportView.as_view(), name="financial_purchase_cost"),
    path("financial/gross-profit/", views.EstimatedGrossProfitReportView.as_view(), name="estimated_gross_profit"),
    path("financial/inventory-value/", views.InventoryValueReportView.as_view(), name="inventory_value"),
    path("financial/average-daily-sales/", views.AverageDailySalesReportView.as_view(), name="average_daily_sales"),
]
