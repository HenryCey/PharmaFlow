from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from apps.common.permissions import PharmaFlowPermissionMixin
from .models import PharmacySettings
from .forms import PharmacySettingsForm


class PharmacySettingsView(PharmaFlowPermissionMixin, UpdateView):
    model = PharmacySettings
    form_class = PharmacySettingsForm
    template_name = "settings_app/settings_form.html"
    success_url = reverse_lazy("settings_app:settings")
    permission_required = "settings_app.change_pharmacysettings"

    def get_object(self, queryset=None):
        return PharmacySettings.load()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Pharmacy settings updated.")
        return response
