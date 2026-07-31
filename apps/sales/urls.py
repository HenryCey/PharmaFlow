from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.POSView.as_view(), name="pos"),
    path("cart/add/", views.CartAddView.as_view(), name="cart_add"),
    path("cart/<int:drug_id>/update/", views.CartUpdateView.as_view(), name="cart_update"),
    path("cart/<int:drug_id>/remove/", views.CartRemoveView.as_view(), name="cart_remove"),
    path("cart/clear/", views.CartClearView.as_view(), name="cart_clear"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),

    path("", views.SaleListView.as_view(), name="sale_list"),
    path("<int:pk>/", views.SaleDetailView.as_view(), name="sale_detail"),
    path("<int:pk>/cancel/", views.SaleCancelView.as_view(), name="sale_cancel"),
    path("<int:pk>/receipt/", views.ReceiptView.as_view(), name="receipt"),
    path("summary/", views.DailySalesSummaryView.as_view(), name="daily_summary"),
]
