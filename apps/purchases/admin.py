from django.contrib import admin

from .models import PurchaseOrder, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ("drug", "quantity", "unit_cost", "selling_price", "batch_number", "subtotal")
    can_delete = False


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("purchase_number", "supplier", "purchase_date", "status", "grand_total", "created_by")
    list_filter = ("status",)
    search_fields = ("purchase_number", "supplier__company_name")
    readonly_fields = ("purchase_number", "subtotal", "grand_total", "received_by", "received_at", "cancelled_by", "cancelled_at")
    inlines = [PurchaseItemInline]

    def has_add_permission(self, request):
        return False  # only ever created via purchase_service.create_purchase_order()
