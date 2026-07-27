"""
Records a LoginHistory row for every login attempt by hooking Django's
built-in auth signals — kept out of the view so it fires no matter which
view triggers authentication (login form, admin, future API, etc.).

Note: despite the filename (kept for now to avoid an extra rename churn),
this module contains signal receivers only — it is imported for its
side effects by AccountsConfig.ready(), not registered as Django
middleware. An earlier version of this file also defined a
`LoginHistoryMiddleware` pass-through class wired into MIDDLEWARE; that
was dead code (ready() already guarantees this module is imported) and
has been removed.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import LoginHistory


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def on_login_success(sender, request, user, **kwargs):
    LoginHistory.objects.create(
        user=user,
        username_attempted=user.username,
        success=True,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
    )


@receiver(user_login_failed)
def on_login_failure(sender, credentials, request=None, **kwargs):
    LoginHistory.objects.create(
        user=None,
        username_attempted=credentials.get("username", ""),
        success=False,
        ip_address=_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255] if request else "",
    )
