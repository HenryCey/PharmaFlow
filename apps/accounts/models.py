"""
accounts models — Users, Roles, Login History.

Maps to the Database Spec's Users / Roles / Permissions entities.
Permissions themselves are NOT a custom model: Django's built-in
Permission + Group system is used directly, with Role as a thin,
business-friendly wrapper around Group (Blueprint: "permissions are
assigned to roles, not directly to users").
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group
from django.db import models

from apps.common.models import TimeStampedModel, SoftDeleteModel
from .managers import UserManager


class Role(TimeStampedModel):
    """
    Business-facing wrapper around a Django Group. The four default roles
    (Owner, Administrator, Pharmacist, Cashier) are created by a data
    migration with baseline permissions attached to their linked Group.
    Custom roles are created the same way through the UI — no code change
    required.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="role", editable=False
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Every Role owns exactly one Group, created transparently so
        # staff managing roles never need to touch /admin/auth/group/.
        # (Checking self.group_id rather than self.group — accessing an
        # unset required OneToOneField raises RelatedObjectDoesNotExist,
        # which hasattr() would not catch.)
        if self.group_id is None:
            self.group = Group.objects.create(name=self.name)
        elif self.group.name != self.name:
            self.group.name = self.name
            self.group.save(update_fields=["name"])
        super().save(*args, **kwargs)

    @property
    def permissions(self):
        return self.group.permissions.all()

    def delete(self, *args, **kwargs):
        # A Role wraps exactly one Group 1:1 — deleting the Role without
        # cleaning up its Group left an orphaned, invisible-to-the-UI
        # auth.Group row behind every time.
        group = self.group
        super().delete(*args, **kwargs)
        group.delete()


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel, TimeStampedModel):
    """Custom user model — required from migration zero per the Database
    Spec (Phone, Role, Status fields don't exist on Django's default User
    and cannot be added to it after the fact)."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name="users", null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    # is_staff controls Django admin access only, kept separate from the
    # business "status" field (active/inactive pharmacy staff member).
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["username"]
        permissions = [
            ("manage_users", "Can create, edit and deactivate users"),
            ("manage_roles", "Can create and edit roles and permissions"),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def get_short_name(self):
        return self.first_name or self.username

    @property
    def is_active(self):
        # Bridges Django auth's expectation of `is_active` onto our
        # business-meaningful `status` field, without duplicating state.
        return self.status == self.STATUS_ACTIVE and not self.is_deleted

    @is_active.setter
    def is_active(self, value):
        self.status = self.STATUS_ACTIVE if value else self.STATUS_INACTIVE


class LoginHistory(models.Model):
    """One row per login attempt, success or failure (Database Spec /
    Feature Specs: Login History, Sensitive Action Logs)."""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="login_history", null=True, blank=True
    )
    username_attempted = models.CharField(max_length=150)
    success = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Login history"

    def __str__(self):
        outcome = "success" if self.success else "failed"
        return f"{self.username_attempted} — {outcome} @ {self.timestamp:%Y-%m-%d %H:%M}"
