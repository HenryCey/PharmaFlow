from decimal import Decimal

from django import forms

from .models import StockAdjustment

DIRECTION_INCREASE = "increase"
DIRECTION_DECREASE = "decrease"
DIRECTION_CHOICES = [
    (DIRECTION_INCREASE, "Increase stock"),
    (DIRECTION_DECREASE, "Decrease stock"),
]


class StockAdjustmentForm(forms.ModelForm):
    """
    Root-cause fix (QA-reported bug): StockAdjustment.quantity is stored
    as a signed value (positive = add, negative = remove), but the form
    used to expose that raw signed field directly - nothing told the
    user that "Damage: 20" needed to be typed as -20, so a naive positive
    entry silently increased stock instead of decreasing it.

    Fixed by splitting the signed value into two explicit, unambiguous
    inputs: `direction` (Increase/Decrease) and `quantity` (a plain
    positive magnitude). The view combines them into the actual signed
    value before calling stock.services.create_adjustment() - the model
    and ledger semantics haven't changed, only how a person enters the
    number. `direction` isn't auto-selected from `adjustment_type`
    because Correction can legitimately go either way.
    """

    direction = forms.ChoiceField(choices=DIRECTION_CHOICES)
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "any"}),
        help_text="Enter a positive amount - Direction above determines add vs. remove.",
    )

    class Meta:
        model = StockAdjustment
        fields = ["adjustment_type", "quantity", "reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 2}),
        }

    def get_signed_quantity(self):
        magnitude = self.cleaned_data["quantity"]
        if self.cleaned_data["direction"] == DIRECTION_DECREASE:
            return -magnitude
        return magnitude
