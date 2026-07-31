from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("drug", "quantity", "unit_price", "discount")
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "customer", "cashier", "payment_method", "total", "status", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("receipt_number", "customer__name", "customer__phone")
    readonly_fields = ("receipt_number", "cashier", "total", "cancelled_by", "cancelled_at")
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False  # Sales are only ever created via checkout_service.complete_sale()
