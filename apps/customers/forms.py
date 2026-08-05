from django import forms

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "address"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_phone(self):
        """Same fix, same reasoning, as DrugForm.clean_sku() — Customer.phone
        is unique=True and Customer is soft-deletable, so Django's built-in
        validate_unique() (which uses the alive-only default manager) can
        miss a soft-deleted customer's phone number still occupying the
        real DB constraint, surfacing a raw IntegrityError instead."""
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone:
            conflict = Customer.all_objects.filter(phone=phone).exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError("A customer with this phone number already exists.")
        return phone
