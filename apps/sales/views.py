from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, View, FormView, ListView, DetailView

from apps.common.permissions import PharmaFlowPermissionMixin
from apps.inventory.models import Drug
from apps.stock.services import InsufficientStockError

from . import cart_service, sales_service
from .checkout_service import complete_sale, EmptyCartError
from .forms import AddToCartForm, CheckoutForm, SaleCancelForm
from .models import Sale
from .receipt_service import get_receipt_context
from .sales_service import SaleAlreadyCancelledError


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _render_cart_panel(request):
    return render(request, "sales/partials/_cart_panel.html", {
        "cart_lines": cart_service.get_cart_lines(request.session),
        "cart_subtotal": cart_service.get_cart_subtotal(request.session),
    })


# ---------------------------------------------------------------------------
# POS + Cart
# ---------------------------------------------------------------------------

class POSView(PharmaFlowPermissionMixin, TemplateView):
    template_name = "sales/pos.html"
    permission_required = "sales.add_sale"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q")
        results = []
        if query:
            results = Drug.objects.filter(status="active").filter(
                Q(name__icontains=query) | Q(generic_name__icontains=query)
                | Q(brand_name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query)
            ).select_related("unit")[:15]
        context["search_query"] = query or ""
        context["search_results"] = results
        context["cart_lines"] = cart_service.get_cart_lines(self.request.session)
        context["cart_subtotal"] = cart_service.get_cart_subtotal(self.request.session)
        return context


class CartAddView(PharmaFlowPermissionMixin, View):
    permission_required = "sales.add_sale"

    def post(self, request, *args, **kwargs):
        form = AddToCartForm(request.POST)
        if form.is_valid():
            cart_service.add_item(
                request.session,
                form.cleaned_data["drug_id"].pk,
                form.cleaned_data["quantity"],
            )
        if _is_htmx(request):
            return _render_cart_panel(request)
        return redirect("sales:pos")


class CartUpdateView(PharmaFlowPermissionMixin, View):
    permission_required = "sales.add_sale"

    def post(self, request, drug_id, *args, **kwargs):
        quantity = request.POST.get("quantity", "0")
        try:
            cart_service.set_item_quantity(request.session, drug_id, quantity)
        except InvalidOperation:
            messages.error(request, "Invalid quantity.")
        if _is_htmx(request):
            return _render_cart_panel(request)
        return redirect("sales:pos")


class CartRemoveView(PharmaFlowPermissionMixin, View):
    permission_required = "sales.add_sale"

    def post(self, request, drug_id, *args, **kwargs):
        cart_service.remove_item(request.session, drug_id)
        if _is_htmx(request):
            return _render_cart_panel(request)
        return redirect("sales:pos")


class CartClearView(PharmaFlowPermissionMixin, View):
    permission_required = "sales.add_sale"

    def post(self, request, *args, **kwargs):
        cart_service.clear(request.session)
        if _is_htmx(request):
            return _render_cart_panel(request)
        return redirect("sales:pos")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

class CheckoutView(PharmaFlowPermissionMixin, FormView):
    template_name = "sales/checkout.html"
    form_class = CheckoutForm
    permission_required = "sales.add_sale"

    def get(self, request, *args, **kwargs):
        if cart_service.is_empty(request.session):
            messages.error(request, "Your cart is empty — add drugs before checking out.")
            return redirect("sales:pos")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart_lines"] = cart_service.get_cart_lines(self.request.session)
        context["cart_subtotal"] = cart_service.get_cart_subtotal(self.request.session)
        return context

    def form_valid(self, form):
        try:
            sale = complete_sale(
                session=self.request.session,
                cashier=self.request.user,
                customer=form.cleaned_data["customer"],
                payment_method=form.cleaned_data["payment_method"],
                discount=form.cleaned_data["discount"],
            )
        except EmptyCartError:
            messages.error(self.request, "Your cart is empty — add drugs before checking out.")
            return redirect("sales:pos")
        except InsufficientStockError as exc:
            messages.error(self.request, str(exc))
            return redirect("sales:pos")
        messages.success(self.request, f"Sale {sale.receipt_number} completed.")
        return redirect("sales:receipt", pk=sale.pk)


# ---------------------------------------------------------------------------
# Sales history / detail / cancel / receipt / summary
# ---------------------------------------------------------------------------

class SaleListView(PharmaFlowPermissionMixin, ListView):
    template_name = "sales/sale_list.html"
    context_object_name = "sales"
    paginate_by = 20
    permission_required = "sales.view_sale"

    def get_queryset(self):
        return sales_service.get_sales_queryset(self.request.user)


class SaleDetailView(PharmaFlowPermissionMixin, DetailView):
    model = Sale
    template_name = "sales/sale_detail.html"
    context_object_name = "sale"
    permission_required = "sales.view_sale"

    def get_queryset(self):
        # Row-level scoping: a Cashier requesting another cashier's sale
        # gets a plain 404, not a 403 — doesn't leak that the sale exists.
        return sales_service.get_sales_queryset(self.request.user).prefetch_related("items__drug")


class SaleCancelView(PharmaFlowPermissionMixin, FormView):
    template_name = "sales/sale_confirm_cancel.html"
    form_class = SaleCancelForm
    permission_required = "sales.cancel_sale"

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sale"] = self.sale
        return context

    def form_valid(self, form):
        try:
            sales_service.cancel_sale(sale=self.sale, user=self.request.user, reason=form.cleaned_data["reason"])
        except SaleAlreadyCancelledError as exc:
            messages.error(self.request, str(exc))
            return redirect("sales:sale_detail", pk=self.sale.pk)
        messages.success(self.request, f"{self.sale.receipt_number} has been cancelled and stock restored.")
        return redirect("sales:sale_detail", pk=self.sale.pk)


class ReceiptView(PharmaFlowPermissionMixin, DetailView):
    model = Sale
    template_name = "sales/receipt.html"
    context_object_name = "sale"
    permission_required = "sales.view_sale"

    def get_queryset(self):
        return sales_service.get_sales_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_receipt_context(self.object))
        return context


class DailySalesSummaryView(PharmaFlowPermissionMixin, TemplateView):
    template_name = "sales/daily_summary.html"
    permission_required = "sales.view_sale"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cashier = None if self.request.user.has_perm("sales.view_all_sales") else self.request.user
        context["summary"] = sales_service.daily_sales_summary(cashier=cashier)
        return context
