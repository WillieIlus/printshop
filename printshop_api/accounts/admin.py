# accounts/admin.py

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User, Profile, SocialLink, EmailVerificationCode


# ---------- Admin-only forms for the custom User ----------

class UserCreationForm(forms.ModelForm):
    """
    Form used in the Django admin to create new users.
    """
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """
    Form used in the Django admin to update existing users.
    Shows the hashed password as read-only.
    """
    password = ReadOnlyPasswordHashField(label=_("Password"),
                                         help_text=_(
                                             "Raw passwords are not stored, so there is no way to see this "
                                             "user’s password, but you can change the password "
                                             "using <a href=\"../password/\">this form</a>."
                                         ))

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_password(self):
        # Return the initial value regardless of what the user provides.
        return self.initial.get("password")


# ---------- Inlines for Profile and SocialLink ----------

class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0
    fields = ("platform", "username", "url", "is_primary", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = "user"
    extra = 0
    fields = ("bio", "avatar", "website", "location", "birth_date", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


# ---------- User admin ----------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model (email as username).
    """
    form = UserChangeForm
    add_form = UserCreationForm
    model = User

    list_display = ("email", "first_name", "last_name", "role", "email_verified", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "email_verified", "role", "groups")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Verification & role"), {"fields": ("email_verified", "role", "onboarding_completed")}),
        (_("Permissions"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "first_name",
                "last_name",
                "password1",
                "password2",
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
            ),
        }),
    )

    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at")

    inlines = [ProfileInline]


# ---------- Profile & SocialLink admin ----------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "website", "birth_date", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "location")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SocialLinkInline]


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("profile", "platform", "username", "url", "is_primary", "created_at")
    list_filter = ("platform", "is_primary")
    search_fields = ("profile__user__email", "username", "url")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "expires_at", "used_at", "attempts", "created_at")
    list_filter = ("used_at",)
    search_fields = ("user__email", "code")
    readonly_fields = ("created_at", "updated_at")