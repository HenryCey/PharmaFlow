"""
Report filters — Sprint 6.

Per the Sprint 6 brief: "Design filters so they are reusable across
report pages." One Form class declares every filter field any report
might need; each report view passes `fields_needed` to keep only the
ones relevant to it, so a single implementation backs every filter bar
in the Reports module rather than one form per report page.
"""
from django import forms

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.inventory.models import Category, Drug
from apps.purchases.models import PURCHASE_STATUS_CHOICES
from apps.sales.models import PAYMENT_METHOD_CHOICES
from apps.stock.models import ADJUSTMENT_TYPE_CHOICES, MOVEMENT_TYPE_CHOICES
from apps.suppliers.models import Supplier

_DATE_ATTRS = {"type": "date", "class": "rounded-md border border-slate-300 px-2 py-1.5 text-sm"}
_SELECT_ATTRS = {"class": "rounded-md border border-slate-300 px-2 py-1.5 text-sm"}
_TEXT_ATTRS = {"class": "rounded-md border border-slate-300 px-2 py-1.5 text-sm"}

PERIOD_CHOICES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]


class ReportFilterForm(forms.Form):
    """Superset of every filter used across the Reports module. A report
    view narrows this down via `fields_needed`; fields not requested are
    dropped in __init__ so they never render, validate, or get treated
    as a filter for that report."""

    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs=_DATE_ATTRS))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs=_DATE_ATTRS))
    period = forms.ChoiceField(choices=PERIOD_CHOICES, required=False, widget=forms.Select(attrs=_SELECT_ATTRS))
    drug = forms.ModelChoiceField(
        queryset=Drug.objects.all(), required=False, empty_label="All Drugs",
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(status="active"), required=False, empty_label="All Categories",
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(status="active"), required=False, empty_label="All Suppliers",
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(), required=False, empty_label="All Customers",
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    cashier = forms.ModelChoiceField(
        queryset=User.objects.filter(status="active"), required=False, empty_label="All Cashiers",
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    payment_method = forms.ChoiceField(
        choices=[("", "All Payment Methods")] + PAYMENT_METHOD_CHOICES, required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    movement_type = forms.ChoiceField(
        choices=[("", "All Movement Types")] + MOVEMENT_TYPE_CHOICES, required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    adjustment_type = forms.ChoiceField(
        choices=[("", "All Adjustment Types")] + ADJUSTMENT_TYPE_CHOICES, required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    purchase_status = forms.ChoiceField(
        choices=[("", "All Statuses")] + PURCHASE_STATUS_CHOICES, required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
    )
    days = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs=_TEXT_ATTRS))

    def __init__(self, *args, fields_needed=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fields_needed is not None:
            for name in list(self.fields):
                if name not in fields_needed:
                    del self.fields[name]

    def clean(self):
        cleaned = super().clean()
        date_from, date_to = cleaned.get("date_from"), cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", "Date To must be on or after Date From.")
        return cleaned
