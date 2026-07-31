from django.urls import path
from . import views

app_name = "stock"

urlpatterns = [
    path("drugs/<int:drug_pk>/adjust/", views.StockAdjustmentCreateView.as_view(), name="adjustment_create"),
]
