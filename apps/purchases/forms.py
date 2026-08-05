from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.inventory.models import Drug
from apps.suppliers.models import Supplier

from .models import PurchaseOrder


class PurchaseOrderForm(forms.ModelForm):
    """Header fields only — items are handled by PurchaseItemFormSet.
    purchase_number is auto-generated, never user-editable."""

    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "purchase_date", "expected_delivery", "notes", "tax", "discount"]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "tax": forms.NumberInput(attrs={"step": "any"}),
            "discount": forms.NumberInput(attrs={"step": "any"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(status="active")


class PurchaseItemLineForm(forms.Form):
    """One line of a purchase order. A plain Form (not ModelForm) because
    the formset's cleaned data is handed to purchase_service, which
    creates the actual PurchaseItem rows itself — matches how Sales'
    cart lines are plain dicts handed to checkout_service, not a form
    bound directly to SaleItem."""

    drug = forms.ModelChoiceField(queryset=Drug.objects.filter(status="active"))
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "any"}),
    )
    unit_cost = forms.DecimalField(
        min_value=Decimal("0"), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "any"}),
    )
    selling_price = forms.DecimalField(
        min_value=Decimal("0"), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "any"}),
        help_text="Applied to the drug's catalog price once this purchase is received.",
    )
    batch_number = forms.CharField(required=False, max_length=50)
    manufacturing_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    expiry_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean_expiry_date(self):
        """
        QA-reported business rule (tightened in the final QA round): a
        pharmacy must never receive stock that has already expired OR
        expires today — expiry_date <= today is invalid, not just <.
        Enforced here at form-clean time — the earliest possible point —
        rather than in receiving_service, since blocking it here means a
        Purchase Order can never even be saved with such a date to begin
        with, which transitively makes it impossible for one to reach
        receiving at all.
        """
        expiry_date = self.cleaned_data.get("expiry_date")
        if expiry_date and expiry_date <= timezone.localdate():
            raise forms.ValidationError(
                "This batch expires today or has already expired and cannot be received into inventory."
            )
        return expiry_date


class BasePurchaseItemFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        has_item = any(
            form.cleaned_data and not form.cleaned_data.get("DELETE")
            for form in self.forms
        )
        if not has_item:
            raise forms.ValidationError("Add at least one item to this purchase order.")


PurchaseItemFormSet = forms.formset_factory(
    PurchaseItemLineForm, formset=BasePurchaseItemFormSet, extra=1, can_delete=True,
)


class ReceivePurchaseForm(forms.Form):
    """Empty on purpose — receiving needs only a confirmation POST, but a
    Form gives the confirmation template CSRF handling for free via the
    same {% include "components/_input.html" %} conventions if a reason
    or note field is ever added later."""
    pass


class CancelPurchaseForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), help_text="Required — explain why this purchase order is being cancelled.")
