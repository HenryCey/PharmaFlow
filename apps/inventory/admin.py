from django.contrib import admin

from .models import Category, Manufacturer, DosageForm, Unit, Drug


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(DosageForm)
class DosageFormAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = (
        "name", "sku", "barcode", "category", "manufacturer", "unit",
        "cost_price", "selling_price", "current_stock", "status",
    )
    list_filter = ("status", "category", "manufacturer")
    search_fields = ("name", "generic_name", "brand_name", "sku", "barcode")
    readonly_fields = ("current_stock", "created_by", "created_at", "updated_at")
