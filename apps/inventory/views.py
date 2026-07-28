from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, Q
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from apps.common.permissions import PharmaFlowPermissionMixin
from .forms import CategoryForm, ManufacturerForm, DosageFormForm, UnitForm, DrugForm
from .models import Category, Manufacturer, DosageForm, Unit, Drug
from .services import low_stock_drugs


def _badge(label, variant):
    return mark_safe(render_to_string("components/_badge.html", {"label": label, "variant": variant}))


def _status_badge(obj):
    return _badge(obj.get_status_display(), "success" if obj.status == "active" else "neutral")


# ---------------------------------------------------------------------------
# Shared lookup-table CRUD (Categories, Manufacturers, Dosage Forms, Units)
#
# All four share identical fields (name, description, status) and identical
# list/search/actions behaviour, so it's implemented once here per the
# Technical Architecture's "reusable components over duplicate
# implementations" principle, instead of four near-identical view sets.
# ---------------------------------------------------------------------------

class LookupListView(PharmaFlowPermissionMixin, ListView):
    paginate_by = 20
    create_url_name = None
    update_url_name = None
    delete_url_name = None
    add_permission = None
    change_permission = None
    delete_permission = None

    def get_queryset(self):
        qs = self.model.objects.all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(name__icontains=query)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_change = self.request.user.has_perm(self.change_permission)
        can_delete = self.request.user.has_perm(self.delete_permission)
        rows = []
        for obj in context["object_list"]:
            actions = []
            if can_change:
                actions.append(
                    f'<a href="{reverse_lazy(self.update_url_name, args=[obj.pk])}" '
                    f'class="text-primary hover:underline mr-3">Edit</a>'
                )
            if can_delete:
                actions.append(
                    f'<a href="{reverse_lazy(self.delete_url_name, args=[obj.pk])}" '
                    f'class="text-danger hover:underline">Delete</a>'
                )
            rows.append([
                obj.name,
                obj.description or "—",
                _status_badge(obj),
                mark_safe("".join(actions)) if actions else "—",
            ])
        context["table_headers"] = ["Name", "Description", "Status", "Actions"]
        context["table_rows"] = rows
        context["search_query"] = self.request.GET.get("q", "")
        context["add_url"] = (
            reverse_lazy(self.create_url_name) if self.request.user.has_perm(self.add_permission) else None
        )
        return context


class ProtectedDeleteMixin:
    """Catches ProtectedError from an in-use catalog reference (a Drug
    still points at it) and reports it as a normal validation-style
    message instead of a 500 — per the UI Contract: "every failed action
    explains why."""

    protected_message = "This record is used by one or more drugs and cannot be deleted."

    def form_valid(self, form):
        self.object = self.get_object()
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(self.request, self.protected_message)
        else:
            messages.success(self.request, f"{self.object} deleted.")
        return HttpResponseRedirect(self.get_success_url())


# Categories ------------------------------------------------------------

class CategoryListView(LookupListView):
    model = Category
    template_name = "inventory/category_list.html"
    permission_required = "inventory.view_category"
    create_url_name = "inventory:category_create"
    update_url_name = "inventory:category_update"
    delete_url_name = "inventory:category_delete"
    add_permission = "inventory.add_category"
    change_permission = "inventory.change_category"
    delete_permission = "inventory.delete_category"


class CategoryCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category created successfully."
    permission_required = "inventory.add_category"


class CategoryUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category updated successfully."
    permission_required = "inventory.change_category"


class CategoryDeleteView(ProtectedDeleteMixin, PharmaFlowPermissionMixin, DeleteView):
    model = Category
    template_name = "inventory/category_confirm_delete.html"
    success_url = reverse_lazy("inventory:category_list")
    permission_required = "inventory.delete_category"


# Manufacturers -----------------------------------------------------------

class ManufacturerListView(LookupListView):
    model = Manufacturer
    template_name = "inventory/manufacturer_list.html"
    permission_required = "inventory.view_manufacturer"
    create_url_name = "inventory:manufacturer_create"
    update_url_name = "inventory:manufacturer_update"
    delete_url_name = "inventory:manufacturer_delete"
    add_permission = "inventory.add_manufacturer"
    change_permission = "inventory.change_manufacturer"
    delete_permission = "inventory.delete_manufacturer"


class ManufacturerCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Manufacturer
    form_class = ManufacturerForm
    template_name = "inventory/manufacturer_form.html"
    success_url = reverse_lazy("inventory:manufacturer_list")
    success_message = "Manufacturer created successfully."
    permission_required = "inventory.add_manufacturer"


class ManufacturerUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Manufacturer
    form_class = ManufacturerForm
    template_name = "inventory/manufacturer_form.html"
    success_url = reverse_lazy("inventory:manufacturer_list")
    success_message = "Manufacturer updated successfully."
    permission_required = "inventory.change_manufacturer"


class ManufacturerDeleteView(ProtectedDeleteMixin, PharmaFlowPermissionMixin, DeleteView):
    model = Manufacturer
    template_name = "inventory/manufacturer_confirm_delete.html"
    success_url = reverse_lazy("inventory:manufacturer_list")
    permission_required = "inventory.delete_manufacturer"


# Dosage Forms --------------------------------------------------------------

class DosageFormListView(LookupListView):
    model = DosageForm
    template_name = "inventory/dosageform_list.html"
    permission_required = "inventory.view_dosageform"
    create_url_name = "inventory:dosageform_create"
    update_url_name = "inventory:dosageform_update"
    delete_url_name = "inventory:dosageform_delete"
    add_permission = "inventory.add_dosageform"
    change_permission = "inventory.change_dosageform"
    delete_permission = "inventory.delete_dosageform"


class DosageFormCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = DosageForm
    form_class = DosageFormForm
    template_name = "inventory/dosageform_form.html"
    success_url = reverse_lazy("inventory:dosageform_list")
    success_message = "Dosage form created successfully."
    permission_required = "inventory.add_dosageform"


class DosageFormUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = DosageForm
    form_class = DosageFormForm
    template_name = "inventory/dosageform_form.html"
    success_url = reverse_lazy("inventory:dosageform_list")
    success_message = "Dosage form updated successfully."
    permission_required = "inventory.change_dosageform"


class DosageFormDeleteView(ProtectedDeleteMixin, PharmaFlowPermissionMixin, DeleteView):
    model = DosageForm
    template_name = "inventory/dosageform_confirm_delete.html"
    success_url = reverse_lazy("inventory:dosageform_list")
    permission_required = "inventory.delete_dosageform"


# Units -----------------------------------------------------------------

class UnitListView(LookupListView):
    model = Unit
    template_name = "inventory/unit_list.html"
    permission_required = "inventory.view_unit"
    create_url_name = "inventory:unit_create"
    update_url_name = "inventory:unit_update"
    delete_url_name = "inventory:unit_delete"
    add_permission = "inventory.add_unit"
    change_permission = "inventory.change_unit"
    delete_permission = "inventory.delete_unit"


class UnitCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Unit
    form_class = UnitForm
    template_name = "inventory/unit_form.html"
    success_url = reverse_lazy("inventory:unit_list")
    success_message = "Unit created successfully."
    permission_required = "inventory.add_unit"


class UnitUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = "inventory/unit_form.html"
    success_url = reverse_lazy("inventory:unit_list")
    success_message = "Unit updated successfully."
    permission_required = "inventory.change_unit"


class UnitDeleteView(ProtectedDeleteMixin, PharmaFlowPermissionMixin, DeleteView):
    model = Unit
    template_name = "inventory/unit_confirm_delete.html"
    success_url = reverse_lazy("inventory:unit_list")
    permission_required = "inventory.delete_unit"


# ---------------------------------------------------------------------------
# Drug Products
# ---------------------------------------------------------------------------

class DrugListView(PharmaFlowPermissionMixin, ListView):
    model = Drug
    template_name = "inventory/drug_list.html"
    context_object_name = "drugs"
    paginate_by = 20
    permission_required = "inventory.view_drug"

    SORT_FIELDS = {
        "name": "name",
        "cost_price": "cost_price",
        "selling_price": "selling_price",
        "current_stock": "current_stock",
    }

    def get_queryset(self):
        qs = Drug.objects.select_related("category", "manufacturer", "dosage_form", "unit")

        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(generic_name__icontains=query)
                | Q(brand_name__icontains=query)
                | Q(sku__icontains=query)
                | Q(barcode__icontains=query)
            )

        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category_id=category)

        manufacturer = self.request.GET.get("manufacturer")
        if manufacturer:
            qs = qs.filter(manufacturer_id=manufacturer)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        if self.request.GET.get("low_stock") == "1":
            qs = low_stock_drugs(qs)

        sort = self.request.GET.get("sort", "name")
        sort_field = self.SORT_FIELDS.get(sort, "name")
        direction = "-" if self.request.GET.get("dir") == "desc" else ""
        return qs.order_by(f"{direction}{sort_field}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_change = self.request.user.has_perm("inventory.change_drug")
        can_delete = self.request.user.has_perm("inventory.delete_drug")

        status_variants = {"active": "success", "inactive": "neutral", "discontinued": "danger"}

        rows = []
        for drug in context["drugs"]:
            stock_cell = drug.current_stock
            if drug.is_out_of_stock:
                stock_cell = mark_safe(
                    f'<span class="inline-flex items-center gap-1.5 whitespace-nowrap">'
                    f'{stock_cell} {_badge("Out of Stock", "danger")}</span>'
                )
            elif drug.is_low_stock:
                stock_cell = mark_safe(
                    f'<span class="inline-flex items-center gap-1.5 whitespace-nowrap">'
                    f'{stock_cell} {_badge("Low Stock", "warning")}</span>'
                )

            actions = [
                f'<a href="{reverse_lazy("inventory:drug_detail", args=[drug.pk])}" '
                f'class="text-primary hover:underline mr-3">View</a>'
            ]
            if can_change:
                actions.append(
                    f'<a href="{reverse_lazy("inventory:drug_update", args=[drug.pk])}" '
                    f'class="text-primary hover:underline mr-3">Edit</a>'
                )
            if can_delete:
                actions.append(
                    f'<a href="{reverse_lazy("inventory:drug_delete", args=[drug.pk])}" '
                    f'class="text-danger hover:underline">Discontinue</a>'
                )

            rows.append([
                drug.name,
                drug.sku or "—",
                drug.category.name,
                drug.manufacturer.name if drug.manufacturer else "—",
                f"{drug.selling_price}",
                stock_cell,
                _badge(drug.get_status_display(), status_variants.get(drug.status, "neutral")),
                mark_safe("".join(actions)),
            ])

        context["table_headers"] = [
            "Drug Name", "SKU", "Category", "Manufacturer", "Selling Price", "Stock", "Status", "Actions",
        ]
        context["table_rows"] = rows
        context["categories"] = Category.objects.filter(status="active")
        context["manufacturers"] = Manufacturer.objects.filter(status="active")
        context["status_choices"] = Drug.DRUG_STATUS_CHOICES
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_manufacturer"] = self.request.GET.get("manufacturer", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["low_stock"] = self.request.GET.get("low_stock", "")
        context["current_sort"] = self.request.GET.get("sort", "name")
        context["current_dir"] = self.request.GET.get("dir", "asc")
        context["sort_options"] = [
            ("name", "Name"),
            ("cost_price", "Cost Price"),
            ("selling_price", "Selling Price"),
            ("current_stock", "Stock"),
        ]
        context["add_url"] = (
            reverse_lazy("inventory:drug_create") if self.request.user.has_perm("inventory.add_drug") else None
        )
        return context


class DrugDetailView(PharmaFlowPermissionMixin, DetailView):
    model = Drug
    template_name = "inventory/drug_detail.html"
    context_object_name = "drug"
    permission_required = "inventory.view_drug"


class DrugCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Drug
    form_class = DrugForm
    template_name = "inventory/drug_form.html"
    success_url = reverse_lazy("inventory:drug_list")
    success_message = "Drug added successfully."
    permission_required = "inventory.add_drug"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class DrugUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Drug
    form_class = DrugForm
    template_name = "inventory/drug_form.html"
    success_url = reverse_lazy("inventory:drug_list")
    success_message = "Drug updated successfully."
    permission_required = "inventory.change_drug"


class DrugDeleteView(PharmaFlowPermissionMixin, DeleteView):
    """
    Matches UserDeleteView's precedent: despite the generic DeleteView
    base, this discontinues the drug (status + soft delete) rather than
    hard-deleting it, since Sales/Purchases in later sprints must still
    be able to reference a discontinued drug's history.
    """
    model = Drug
    template_name = "inventory/drug_confirm_delete.html"
    success_url = reverse_lazy("inventory:drug_list")
    permission_required = "inventory.delete_drug"

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.status = Drug.STATUS_DISCONTINUED
        self.object.save(update_fields=["status"])
        self.object.delete()  # soft delete (SoftDeleteModel), preserves history
        messages.success(
            self.request,
            f"{self.object} has been discontinued and removed from active inventory listings.",
        )
        return HttpResponseRedirect(self.get_success_url())
