from django import forms

from .models import PharmacySettings


class PharmacySettingsForm(forms.ModelForm):
    class Meta:
        model = PharmacySettings
        fields = [
            "pharmacy_name", "logo", "address", "phone", "email",
            "currency_symbol", "receipt_footer_note", "default_printer_name",
        ]
