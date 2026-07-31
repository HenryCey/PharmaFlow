from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.common.permissions import PharmaFlowPermissionMixin
from apps.inventory.models import Drug

from .forms import StockAdjustmentForm, DIRECTION_INCREASE
from .models import ADJUSTMENT_OPENING_STOCK
from .services import create_adjustment, InsufficientStockError


class StockAdjustmentCreateView(PharmaFlowPermissionMixin, FormView):
    """
    Deliberately not a generic CreateView bound to StockAdjustment directly
    — the target Drug comes from the URL (this view is only ever linked
    to from that drug's detail page), not chosen in the form itself.
    """
    template_name = "stock/adjustment_form.html"
    form_class = StockAdjustmentForm
    permission_required = "stock.add_stockadjustment"

    def dispatch(self, request, *args, **kwargs):
        self.drug = get_object_or_404(Drug, pk=kwargs["drug_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        # Enhancement (QA-requested): a brand-new drug always starts at
        # current_stock=0 (Sprint 2 left it read-only pending this exact
        # module), so it's almost always about to receive its very first
        # Opening Stock entry — default to that instead of making every
        # first-time setup start from "Damage".
        if self.drug.current_stock == 0:
            initial["adjustment_type"] = ADJUSTMENT_OPENING_STOCK
            initial["direction"] = DIRECTION_INCREASE
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drug"] = self.drug
        context["is_zero_stock"] = self.drug.current_stock == 0
        return context

    def form_valid(self, form):
        try:
            create_adjustment(
                drug=self.drug,
                quantity=form.get_signed_quantity(),
                adjustment_type=form.cleaned_data["adjustment_type"],
                reason=form.cleaned_data["reason"],
                user=self.request.user,
            )
        except InsufficientStockError as exc:
            form.add_error("quantity", str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f"Stock adjustment recorded for {self.drug.name}.")
        return redirect("inventory:drug_detail", pk=self.drug.pk)
