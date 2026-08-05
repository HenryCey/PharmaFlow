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
        """
        Root cause of the IntegrityError QA hit: Django's built-in
        ModelForm uniqueness check (validate_unique()) queries through
        the model's default manager — Drug.objects, which is alive-only
        (SoftDeleteManager). A discontinued (soft-deleted) drug's old SKU
        is invisible to that check but still physically occupies the
        column's real UNIQUE constraint, so the check passes and the
        actual INSERT/UPDATE then raises a raw IntegrityError. Fixed by
        checking explicitly against Drug.all_objects here instead.
        """
        sku = (self.cleaned_data.get("sku") or "").strip()
        sku = sku or None
        if sku:
            conflict = Drug.all_objects.filter(sku=sku).exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError("This SKU already exists. Please enter a different SKU.")
        return sku

    def clean_barcode(self):
        """Same fix, same reasoning, as clean_sku() above."""
        barcode = (self.cleaned_data.get("barcode") or "").strip()
        barcode = barcode or None
        if barcode:
            conflict = Drug.all_objects.filter(barcode=barcode).exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError("This barcode already exists. Please enter a different barcode.")
        return barcode
