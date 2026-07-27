from django.contrib import admin

from .models import PharmacySettings, NumberingSequence


@admin.register(PharmacySettings)
class PharmacySettingsAdmin(admin.ModelAdmin):
    list_display = ("pharmacy_name", "currency_symbol", "phone", "email")

    def has_add_permission(self, request):
        # Singleton — creation happens via PharmacySettings.load(), not admin.
        return not PharmacySettings.objects.exists()


@admin.register(NumberingSequence)
class NumberingSequenceAdmin(admin.ModelAdmin):
    list_display = ("document_type", "prefix", "next_number", "padding")
