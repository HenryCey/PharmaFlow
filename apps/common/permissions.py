"""
Route-level permission enforcement, shared by every app.

Views declare the single Django permission string they require
(e.g. "accounts.manage_users") instead of checking request.user.role
directly — Roles are just Groups carrying these permissions, so this
stays correct no matter how roles are configured.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class PharmaFlowPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Base class-based-view mixin: require login AND a specific permission."""

    raise_exception = False  # redirects to LOGIN_URL instead of 403 if not authenticated
    permission_denied_message = "You do not have permission to perform this action."
