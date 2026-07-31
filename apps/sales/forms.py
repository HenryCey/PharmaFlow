from decimal import Decimal

from django import forms

from apps.customers.models import Customer
from apps.inventory.models import Drug

from .models import PAYMENT_METHOD_CHOICES


class AddToCartForm(forms.Form):
    drug_id = forms.ModelChoiceField(queryset=Drug.objects.filter(status="active"), widget=forms.HiddenInput)
    quantity = forms.DecimalField(min_value=Decimal("0.01"), initial=1, max_digits=12, decimal_places=2)


class CheckoutForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(), required=False, empty_label="Walk-in Customer",
    )
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    discount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, initial=0,
    )

    def clean_discount(self):
        return self.cleaned_data.get("discount") or Decimal("0")


class SaleCancelForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), help_text="Required — explain why this sale is being cancelled.")
