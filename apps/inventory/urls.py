from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # Manufacturers
    path("manufacturers/", views.ManufacturerListView.as_view(), name="manufacturer_list"),
    path("manufacturers/new/", views.ManufacturerCreateView.as_view(), name="manufacturer_create"),
    path("manufacturers/<int:pk>/edit/", views.ManufacturerUpdateView.as_view(), name="manufacturer_update"),
    path("manufacturers/<int:pk>/delete/", views.ManufacturerDeleteView.as_view(), name="manufacturer_delete"),

    # Dosage Forms
    path("dosage-forms/", views.DosageFormListView.as_view(), name="dosageform_list"),
    path("dosage-forms/new/", views.DosageFormCreateView.as_view(), name="dosageform_create"),
    path("dosage-forms/<int:pk>/edit/", views.DosageFormUpdateView.as_view(), name="dosageform_update"),
    path("dosage-forms/<int:pk>/delete/", views.DosageFormDeleteView.as_view(), name="dosageform_delete"),

    # Units
    path("units/", views.UnitListView.as_view(), name="unit_list"),
    path("units/new/", views.UnitCreateView.as_view(), name="unit_create"),
    path("units/<int:pk>/edit/", views.UnitUpdateView.as_view(), name="unit_update"),
    path("units/<int:pk>/delete/", views.UnitDeleteView.as_view(), name="unit_delete"),

    # Drugs (Drug Products)
    path("drugs/", views.DrugListView.as_view(), name="drug_list"),
    path("drugs/new/", views.DrugCreateView.as_view(), name="drug_create"),
    path("drugs/<int:pk>/", views.DrugDetailView.as_view(), name="drug_detail"),
    path("drugs/<int:pk>/edit/", views.DrugUpdateView.as_view(), name="drug_update"),
    path("drugs/<int:pk>/delete/", views.DrugDeleteView.as_view(), name="drug_delete"),
]
