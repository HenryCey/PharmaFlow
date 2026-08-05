from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_code", "company_name", "phone", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("supplier_code", "company_name", "phone", "email")
    readonly_fields = ("supplier_code", "created_by", "created_at", "updated_at")
