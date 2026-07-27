from django.contrib.auth.base_user import BaseUserManager

from apps.common.models import SoftDeleteQuerySet


class UserManager(BaseUserManager):
    """
    Custom manager for the custom User model. Username remains the login
    identifier (Database Spec lists Username as a distinct required field
    from Email, and Email is optional), so we don't use Django's default
    email-as-username assumption.

    Bug fix (Sprint 1 v1.0.1): this manager previously overrode
    SoftDeleteModel's `objects` manager outright, so `User.objects.all()`
    never filtered out soft-deleted rows. get_queryset() now applies the
    same alive()-only filtering as every other soft-deletable model.
    """

    use_in_migrations = True

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Users must have a username.")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "active")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(username, password, **extra_fields)
