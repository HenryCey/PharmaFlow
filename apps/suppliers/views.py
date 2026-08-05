from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from apps.common.permissions import PharmaFlowPermissionMixin

from .forms import SupplierForm
from .models import Supplier
from .services import create_supplier


class SupplierListView(PharmaFlowPermissionMixin, ListView):
    model = Supplier
    template_name = "suppliers/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 20
    permission_required = "suppliers.view_supplier"

    def get_queryset(self):
        qs = Supplier.objects.all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(company_name__icontains=query) | Q(supplier_code__icontains=query)
                | Q(contact_person__icontains=query) | Q(phone__icontains=query)
            )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("company_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_change = self.request.user.has_perm("suppliers.change_supplier")
        can_delete = self.request.user.has_perm("suppliers.delete_supplier")
        rows = []
        for supplier in context["suppliers"]:
            actions = [
                f'<a href="{reverse_lazy("suppliers:supplier_detail", args=[supplier.pk])}" '
                f'class="text-primary hover:underline mr-3">View</a>'
            ]
            if can_change:
                actions.append(
                    f'<a href="{reverse_lazy("suppliers:supplier_update", args=[supplier.pk])}" '
                    f'class="text-primary hover:underline mr-3">Edit</a>'
                )
            if can_delete:
                actions.append(
                    f'<a href="{reverse_lazy("suppliers:supplier_delete", args=[supplier.pk])}" '
                    f'class="text-danger hover:underline">Delete</a>'
                )
            rows.append([
                supplier.supplier_code, supplier.company_name, supplier.contact_person or "—",
                supplier.phone, supplier.city or "—",
                "Active" if supplier.status == "active" else "Inactive",
                mark_safe("".join(actions)),
            ])
        context["table_headers"] = ["Code", "Supplier Name", "Contact Person", "Phone", "City", "Status", "Actions"]
        context["table_rows"] = rows
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["add_url"] = (
            reverse_lazy("suppliers:supplier_create") if self.request.user.has_perm("suppliers.add_supplier") else None
        )
        return context


class SupplierDetailView(PharmaFlowPermissionMixin, DetailView):
    model = Supplier
    template_name = "suppliers/supplier_detail.html"
    context_object_name = "supplier"
    permission_required = "suppliers.view_supplier"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # `purchase_orders` is the reverse accessor from PurchaseOrder.supplier
        # (defined in apps/purchases) — resolved at runtime via the app
        # registry, no import-time dependency of suppliers on purchases.
        orders = self.object.purchase_orders.order_by("-created_at")
        stats = orders.exclude(status="cancelled").aggregate(
            total=Sum("grand_total"), count=Count("id")
        )
        outstanding = orders.filter(status="ordered").aggregate(total=Sum("grand_total"))
        context["recent_purchases"] = orders[:20]
        context["total_purchases"] = stats["total"] or 0
        context["purchase_count"] = stats["count"] or 0
        context["outstanding_purchases"] = outstanding["total"] or 0
        context["last_purchase"] = orders.first()
        return context


class SupplierCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_form.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    success_message = "Supplier added successfully."
    permission_required = "suppliers.add_supplier"

    def form_valid(self, form):
        supplier = create_supplier(created_by=self.request.user, **form.cleaned_data)
        self.object = supplier
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())


class SupplierUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_form.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    success_message = "Supplier updated successfully."
    permission_required = "suppliers.change_supplier"


class SupplierDeleteView(PharmaFlowPermissionMixin, DeleteView):
    model = Supplier
    template_name = "suppliers/supplier_confirm_delete.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    permission_required = "suppliers.delete_supplier"

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.delete()  # soft delete (SoftDeleteModel) - preserves Purchase history
        messages.success(self.request, f"{self.object} has been removed from active suppliers.")
        return HttpResponseRedirect(self.get_success_url())
