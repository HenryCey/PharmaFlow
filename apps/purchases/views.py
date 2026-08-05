from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import ListView, DetailView, View, TemplateView

from apps.common.permissions import PharmaFlowPermissionMixin
from apps.suppliers.models import Supplier

from .forms import PurchaseOrderForm, PurchaseItemFormSet, CancelPurchaseForm
from .models import PurchaseOrder, PurchaseItem, STATUS_RECEIVED
from .purchase_service import (
    create_purchase_order, update_purchase_order, place_order, cancel_purchase_order,
    PurchaseOrderNotEditableError, InvalidStatusTransitionError,
)
from .receiving_service import receive_purchase


def _badge(label, variant):
    return mark_safe(render_to_string("components/_badge.html", {"label": label, "variant": variant}))


def _actions_dropdown(items):
    """Reuses the existing _dropdown.html component (same one Sprint 3's
    Drug List uses) — the component itself needs its caller to supply the
    Alpine `open` state, since it doesn't declare x-data on its own."""
    dropdown_html = render_to_string(
        "components/_dropdown.html", {"trigger_label": "Actions", "items": items}
    )
    return mark_safe(f'<div x-data="{{ open: false }}">{dropdown_html}</div>')


STATUS_VARIANTS = {"draft": "neutral", "ordered": "warning", "received": "success", "cancelled": "danger"}


def _items_from_formset(formset):
    """Extracts clean item dicts from a valid formset, skipping rows
    marked for deletion or left entirely blank (the extra empty row)."""
    items = []
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        data = form.cleaned_data.copy()
        data.pop("DELETE", None)
        items.append(data)
    return items


# ---------------------------------------------------------------------------
# List / Detail / Print
# ---------------------------------------------------------------------------

class PurchaseOrderListView(PharmaFlowPermissionMixin, ListView):
    """Doubles as the "Purchase History" operational report — filterable
    by supplier, which also covers "Supplier Purchases" without a
    separate report page (Supplier detail additionally shows its own
    scoped history)."""
    model = PurchaseOrder
    template_name = "purchases/purchase_list.html"
    context_object_name = "purchases"
    paginate_by = 20
    permission_required = "purchases.view_purchaseorder"

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("supplier")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(purchase_number__icontains=query) | Q(supplier__company_name__icontains=query))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        supplier = self.request.GET.get("supplier")
        if supplier:
            qs = qs.filter(supplier_id=supplier)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_change = self.request.user.has_perm("purchases.change_purchaseorder")
        can_receive = self.request.user.has_perm("purchases.receive_purchaseorder")
        can_cancel = self.request.user.has_perm("purchases.cancel_purchaseorder")

        rows = []
        for order in context["purchases"]:
            detail_url = reverse_lazy("purchases:purchase_detail", args=[order.pk])
            print_url = reverse_lazy("purchases:purchase_print", args=[order.pk])

            # QA-specified action set per status — makes the workflow
            # discoverable from the list itself, instead of relying on
            # the purchase number being (non-obviously) clickable.
            action_items = [{"label": "View", "url": detail_url}]
            if order.status == "draft":
                if can_change:
                    action_items.append({"label": "Edit", "url": reverse_lazy("purchases:purchase_update", args=[order.pk])})
                    action_items.append({"label": "Place Order", "url": detail_url})
                if can_cancel:
                    action_items.append({"label": "Cancel", "url": reverse_lazy("purchases:purchase_cancel", args=[order.pk]), "danger": True})
            elif order.status == "ordered":
                if can_receive:
                    action_items.append({"label": "Receive Purchase", "url": detail_url})
                action_items.append({"label": "Print", "url": print_url})
            else:  # received or cancelled
                action_items.append({"label": "Print", "url": print_url})

            rows.append([
                mark_safe(f'<a href="{detail_url}" class="text-primary hover:underline">{order.purchase_number}</a>'),
                order.supplier.company_name,
                order.purchase_date,
                order.grand_total,
                _badge(order.get_status_display(), STATUS_VARIANTS.get(order.status, "neutral")),
                _actions_dropdown(action_items),
            ])
        context["table_headers"] = ["Purchase #", "Supplier", "Date", "Grand Total", "Status", "Actions"]
        context["table_rows"] = rows
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_supplier"] = self.request.GET.get("supplier", "")
        context["suppliers"] = Supplier.objects.filter(status="active")
        context["status_choices"] = PurchaseOrder._meta.get_field("status").choices
        context["add_url"] = (
            reverse_lazy("purchases:purchase_create") if self.request.user.has_perm("purchases.add_purchaseorder") else None
        )
        return context


class PurchaseOrderDetailView(PharmaFlowPermissionMixin, DetailView):
    model = PurchaseOrder
    template_name = "purchases/purchase_detail.html"
    context_object_name = "purchase"
    permission_required = "purchases.view_purchaseorder"

    def get_queryset(self):
        return PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("items__drug")


class PurchaseOrderPrintView(PharmaFlowPermissionMixin, DetailView):
    model = PurchaseOrder
    template_name = "purchases/purchase_print.html"
    context_object_name = "purchase"
    permission_required = "purchases.view_purchaseorder"

    def get_queryset(self):
        return PurchaseOrder.objects.select_related("supplier").prefetch_related("items__drug")


# ---------------------------------------------------------------------------
# Create / Update (form + item formset together)
# ---------------------------------------------------------------------------

class PurchaseOrderCreateView(PharmaFlowPermissionMixin, View):
    permission_required = "purchases.add_purchaseorder"
    template_name = "purchases/purchase_form.html"

    def get(self, request, *args, **kwargs):
        initial = {}
        supplier_id = request.GET.get("supplier")
        if supplier_id:
            initial["supplier"] = supplier_id
        form = PurchaseOrderForm(initial=initial)
        formset = PurchaseItemFormSet()
        return self._render(request, form, formset)

    def post(self, request, *args, **kwargs):
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            order = create_purchase_order(
                supplier=form.cleaned_data["supplier"],
                purchase_date=form.cleaned_data["purchase_date"],
                expected_delivery=form.cleaned_data["expected_delivery"],
                notes=form.cleaned_data["notes"],
                tax=form.cleaned_data["tax"] or 0,
                discount=form.cleaned_data["discount"] or 0,
                created_by=request.user,
                items=_items_from_formset(formset),
            )
            messages.success(request, f"Purchase order {order.purchase_number} created as Draft.")
            return redirect("purchases:purchase_detail", pk=order.pk)
        return self._render(request, form, formset)

    def _render(self, request, form, formset):
        return render(request, self.template_name, {"form": form, "formset": formset, "object": None})


class PurchaseOrderUpdateView(PharmaFlowPermissionMixin, View):
    permission_required = "purchases.change_purchaseorder"
    template_name = "purchases/purchase_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(PurchaseOrder, pk=kwargs["pk"])
        if not self.order.is_editable:
            messages.error(request, f"{self.order.purchase_number} is {self.order.get_status_display()} and can no longer be edited.")
            return redirect("purchases:purchase_detail", pk=self.order.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = PurchaseOrderForm(instance=self.order)
        initial = [
            {
                "drug": item.drug_id, "quantity": item.quantity, "unit_cost": item.unit_cost,
                "selling_price": item.selling_price, "batch_number": item.batch_number,
                "manufacturing_date": item.manufacturing_date, "expiry_date": item.expiry_date,
            }
            for item in self.order.items.all()
        ]
        # extra=1 (formset default) is intentionally left as-is here: with
        # min_num removed (see forms.py), total_form_count() = len(initial)
        # + extra, giving exactly the existing items plus one blank row to
        # add a new line — no manual adjustment needed.
        formset = PurchaseItemFormSet(initial=initial)
        return self._render(request, form, formset)

    def post(self, request, *args, **kwargs):
        form = PurchaseOrderForm(request.POST, instance=self.order)
        formset = PurchaseItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            try:
                update_purchase_order(
                    order=self.order,
                    purchase_date=form.cleaned_data["purchase_date"],
                    expected_delivery=form.cleaned_data["expected_delivery"],
                    notes=form.cleaned_data["notes"],
                    tax=form.cleaned_data["tax"] or 0,
                    discount=form.cleaned_data["discount"] or 0,
                    items=_items_from_formset(formset),
                )
            except PurchaseOrderNotEditableError as exc:
                messages.error(request, str(exc))
                return redirect("purchases:purchase_detail", pk=self.order.pk)
            messages.success(request, f"{self.order.purchase_number} updated.")
            return redirect("purchases:purchase_detail", pk=self.order.pk)
        return self._render(request, form, formset)

    def _render(self, request, form, formset):
        return render(request, self.template_name, {"form": form, "formset": formset, "object": self.order})


# ---------------------------------------------------------------------------
# Status-changing actions
# ---------------------------------------------------------------------------

class PlaceOrderView(PharmaFlowPermissionMixin, View):
    permission_required = "purchases.change_purchaseorder"

    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            place_order(order=order)
        except InvalidStatusTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{order.purchase_number} marked as Ordered.")
        return redirect("purchases:purchase_detail", pk=pk)


class ReceivePurchaseView(PharmaFlowPermissionMixin, View):
    permission_required = "purchases.receive_purchaseorder"

    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            receive_purchase(purchase=order, user=request.user)
        except InvalidStatusTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{order.purchase_number} received — stock updated.")
        return redirect("purchases:purchase_detail", pk=pk)


class CancelPurchaseView(PharmaFlowPermissionMixin, View):
    permission_required = "purchases.cancel_purchaseorder"
    template_name = "purchases/purchase_confirm_cancel.html"

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(PurchaseOrder, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"purchase": self.order, "form": CancelPurchaseForm()})

    def post(self, request, *args, **kwargs):
        form = CancelPurchaseForm(request.POST)
        if form.is_valid():
            try:
                cancel_purchase_order(order=self.order, user=request.user, reason=form.cleaned_data["reason"])
            except InvalidStatusTransitionError as exc:
                messages.error(request, str(exc))
                return redirect("purchases:purchase_detail", pk=self.order.pk)
            messages.success(request, f"{self.order.purchase_number} cancelled.")
            return redirect("purchases:purchase_detail", pk=self.order.pk)
        return render(request, self.template_name, {"purchase": self.order, "form": form})


# ---------------------------------------------------------------------------
# Recently Received Stock (operational report)
# ---------------------------------------------------------------------------

class RecentlyReceivedStockView(PharmaFlowPermissionMixin, TemplateView):
    template_name = "purchases/recently_received.html"
    permission_required = "purchases.view_purchaseorder"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = (
            PurchaseItem.objects.filter(purchase__status=STATUS_RECEIVED)
            .select_related("drug", "purchase", "purchase__supplier")
            .order_by("-purchase__received_at")[:50]
        )
        return context
