from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm as DjangoPasswordChangeForm

from .models import User, Role


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "This account is inactive. Contact an administrator.",
    }


class PasswordChangeForm(DjangoPasswordChangeForm):
    """Thin wrapper kept so templates/tests reference apps.accounts, not
    django.contrib.auth directly — future custom validation goes here."""


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=False,
        help_text="Leave blank to keep the current password when editing.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "role", "status"]
        widgets = {
            "status": forms.Select(),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        # Bug fix (v1.0.2): strip incidental whitespace so a value that is
        # only whitespace is treated as "left blank," not as a new password.
        raw_password = (self.cleaned_data.get("password") or "").strip()
        if raw_password:
            # Django's set_password() hashes before it ever touches the
            # database — this was already correct; the reported symptom
            # traced to the input missing autocomplete="new-password"
            # above, which let some browsers silently autofill a different
            # saved credential into the field.
            user.set_password(raw_password)
        if commit:
            user.save()
        return user


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name", "description"]
