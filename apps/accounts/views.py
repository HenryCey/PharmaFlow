from django.contrib.auth import views as auth_views, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from apps.common.permissions import PharmaFlowPermissionMixin
from .forms import LoginForm, PasswordChangeForm, UserForm, RoleForm
from .models import User, Role


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class PasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy("accounts:password_change")
    success_message = "Your password has been updated."


# ---------------------------------------------------------------------------
# User management (Phase 1 / Sprint 1 — "Users can log in and navigate")
# ---------------------------------------------------------------------------

class UserListView(PharmaFlowPermissionMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 20
    permission_required = "accounts.manage_users"

    def get_queryset(self):
        qs = User.objects.select_related("role").all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(username__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["table_headers"] = ["Username", "Full Name", "Role", "Status", "Actions"]
        context["table_rows"] = [
            [
                user.username,
                user.get_full_name(),
                user.role.name if user.role else "—",
                self._status_badge(user),
                self._row_actions(user),
            ]
            for user in context["users"]
        ]
        context["add_url"] = reverse_lazy("accounts:user_create")
        return context

    @staticmethod
    def _status_badge(user):
        from django.template.loader import render_to_string
        from django.utils.safestring import mark_safe
        variant = "success" if user.status == User.STATUS_ACTIVE else "neutral"
        return mark_safe(render_to_string(
            "components/_badge.html", {"label": user.get_status_display(), "variant": variant}
        ))

    @staticmethod
    def _row_actions(user):
        from django.utils.safestring import mark_safe
        edit_url = reverse_lazy("accounts:user_update", args=[user.pk])
        delete_url = reverse_lazy("accounts:user_delete", args=[user.pk])
        return mark_safe(
            f'<a href="{edit_url}" class="text-primary hover:underline mr-3">Edit</a>'
            f'<a href="{delete_url}" class="text-danger hover:underline">Deactivate</a>'
        )


class UserCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "User created successfully."
    permission_required = "accounts.manage_users"


class UserUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "User updated successfully."
    permission_required = "accounts.manage_users"


class UserDeleteView(PharmaFlowPermissionMixin, DeleteView):
    """
    Despite the generic DeleteView base class, this performs a
    deactivation, not a deletion — matching the button's own label and
    the confirmation page's own copy ("They will no longer be able to
    log in").

    Bug fix (Sprint 1 v1.0.1): this previously called self.object.delete()
    (a soft delete), which only ever touches is_deleted/deleted_at — the
    `status` field the Users list actually displays was never updated, so
    the row kept showing "Active" after a successful deactivation.
    """
    model = User
    template_name = "accounts/user_confirm_delete.html"
    success_url = reverse_lazy("accounts:user_list")
    permission_required = "accounts.manage_users"

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.status = User.STATUS_INACTIVE
        self.object.save(update_fields=["status"])
        from django.contrib import messages
        messages.success(self.request, f"{self.object} has been deactivated and can no longer log in.")
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

class RoleListView(PharmaFlowPermissionMixin, ListView):
    model = Role
    template_name = "accounts/role_list.html"
    context_object_name = "roles"
    permission_required = "accounts.manage_roles"

    def get_context_data(self, **kwargs):
        from django.utils.safestring import mark_safe

        context = super().get_context_data(**kwargs)
        context["table_headers"] = ["Role", "Description", "Users", "Actions"]
        context["table_rows"] = [
            [
                role.name,
                role.description or "—",
                role.users.count(),
                mark_safe(
                    f'<a href="{reverse_lazy("accounts:role_update", args=[role.pk])}" class="text-primary hover:underline mr-3">Edit</a>'
                    f'<a href="{reverse_lazy("accounts:role_delete", args=[role.pk])}" class="text-danger hover:underline">Delete</a>'
                ),
            ]
            for role in context["roles"]
        ]
        context["add_url"] = reverse_lazy("accounts:role_create")
        return context


class RoleCreateView(PharmaFlowPermissionMixin, SuccessMessageMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = "accounts/role_form.html"
    success_url = reverse_lazy("accounts:role_list")
    success_message = "Role created successfully."
    permission_required = "accounts.manage_roles"


class RoleUpdateView(PharmaFlowPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = "accounts/role_form.html"
    success_url = reverse_lazy("accounts:role_list")
    success_message = "Role updated successfully."
    permission_required = "accounts.manage_roles"


class RoleDeleteView(PharmaFlowPermissionMixin, DeleteView):
    model = Role
    template_name = "accounts/role_confirm_delete.html"
    success_url = reverse_lazy("accounts:role_list")
    permission_required = "accounts.manage_roles"
