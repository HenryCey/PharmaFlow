from django.contrib import admin

from .models import InventoryMovement, StockAdjustment


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("drug", "movement_type", "quantity", "reference", "user", "created_at")
    list_filter = ("movement_type",)
    search_fields = ("drug__name", "reference")
    readonly_fields = [f.name for f in InventoryMovement._meta.fields]  # append-only ledger

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("drug", "adjustment_type", "quantity", "recorded_by", "created_at")
    list_filter = ("adjustment_type",)
    search_fields = ("drug__name", "reason")
    readonly_fields = ("recorded_by", "created_at", "updated_at")
