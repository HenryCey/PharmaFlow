"""Development environment settings."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Simplest possible local mail backend for password-reset emails during dev.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
