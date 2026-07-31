from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from apps.common.permissions import PharmaFlowPermissionMixin

from .forms import CustomerForm
from .models import Customer


class CustomerListView(PharmaFlowPermissionMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20
    permission_required = "customers.view_customer"

    def get_queryset(self):
        qs = Customer.objects.all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query))
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_change = self.request.user.has_perm("customers.change_customer")
        can_delete = self.request.user.has_perm("customers.delete_customer")
        rows = []
        for customer in context["customers"]:
            actions = [
                f'<a href="{reverse_lazy("customers:customer_detail", args=[customer.pk])}" '
                f'class="text-primary hover:underline mr-3">View</a>'
            ]
            if can_change:
                actions.append(
                    f'<a href="{reverse_lazy("customers:customer_update", args=[customer.pk])}" '
                    f'class="text-primary hover:underline mr-3">Edit</a>'
                )
            if can_delete:
                actions.append(
                    f'<a href="{reverse_lazy("customers:customer_delete", args=[customer.pk])}" '
                    f'class="text-danger hover:underline">Delete</a>'
                )
            rows.append([customer.name, customer.phone, customer.address or "—", mark_safe("".join(actions))])
        context["table_headers"] = ["Name", "Phone", "Address", "Actions"]
        context["table_rows"] = rows
        context["search_query"] = self.request.GET.get("q", "")
        context["add_url"] = (
            reverse_lazy("customers:customer_create") if self.request.user.has_perm("customers.add_customer") else None
        )
        return context


class CustomerDetailView(PharmaFlowPermissionMixin, DetailView):
    model = Customer
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"
    permission_required = "customers.view_customer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Feature Specs: Customers module includes "Purchase History".
        # `sales` is the reverse accessor from Sale.customer (defined in
        # apps/sales) — resolved at runtime via the app registry, so
        # customers has no import-time dependency on sales.
        context["recent_sales"] = self.object.sales.order_by("-created_at")[:20]
        return context


class CustomerCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")
    success_message = "Customer added successfully."
    permission_required = "customers.add_customer"


class CustomerUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")
    success_message = "Customer updated successfully."
    permission_required = "customers.change_customer"


class CustomerDeleteView(PharmaFlowPermissionMixin, DeleteView):
    model = Customer
    template_name = "customers/customer_confirm_delete.html"
    success_url = reverse_lazy("customers:customer_list")
    permission_required = "customers.delete_customer"

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.delete()  # soft delete (SoftDeleteModel) — preserves Sales history
        messages.success(self.request, f"{self.object} has been removed from active customers.")
        return HttpResponseRedirect(self.get_success_url())
