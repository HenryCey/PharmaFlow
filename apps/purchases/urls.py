from django.urls import path
from . import views

app_name = "purchases"

urlpatterns = [
    path("", views.PurchaseOrderListView.as_view(), name="purchase_list"),
    path("new/", views.PurchaseOrderCreateView.as_view(), name="purchase_create"),
    path("received/", views.RecentlyReceivedStockView.as_view(), name="recently_received"),
    path("<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="purchase_detail"),
    path("<int:pk>/edit/", views.PurchaseOrderUpdateView.as_view(), name="purchase_update"),
    path("<int:pk>/print/", views.PurchaseOrderPrintView.as_view(), name="purchase_print"),
    path("<int:pk>/place-order/", views.PlaceOrderView.as_view(), name="purchase_place_order"),
    path("<int:pk>/receive/", views.ReceivePurchaseView.as_view(), name="purchase_receive"),
    path("<int:pk>/cancel/", views.CancelPurchaseView.as_view(), name="purchase_cancel"),
]
