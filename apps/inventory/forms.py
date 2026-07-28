from django import forms

from .models import Category, Manufacturer, DosageForm, Unit, Drug


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "status"]


class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer
        fields = ["name", "description", "status"]


class DosageFormForm(forms.ModelForm):
    class Meta:
        model = DosageForm
        fields = ["name", "description", "status"]


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name", "description", "status"]


class DrugForm(forms.ModelForm):
    """
    current_stock is deliberately NOT in this form — see Drug's docstring
    in models.py. It stays at its default (0 on create, unchanged on
    edit) until the `stock` app owns writing it via ledger transactions.
    """

    class Meta:
        model = Drug
        fields = [
            "name", "generic_name", "brand_name", "sku", "barcode",
            "category", "manufacturer", "dosage_form", "unit", "strength",
            "description", "cost_price", "selling_price",
            "minimum_stock", "reorder_level", "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_sku(self):
        sku = (self.cleaned_data.get("sku") or "").strip()
        return sku or None

    def clean_barcode(self):
        barcode = (self.cleaned_data.get("barcode") or "").strip()
        return barcode or None
