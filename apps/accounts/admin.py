from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Membership, SignupInvitation, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_staff", "is_active"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Infos personnelles", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    search_fields = ["email"]


admin.site.register(Membership)


@admin.register(SignupInvitation)
class SignupInvitationAdmin(admin.ModelAdmin):
    """The list of invited addresses: add one to let a person sign up."""

    list_display = ["email", "note", "created_at", "used_at"]
    search_fields = ["email", "note"]
    readonly_fields = ["used_at"]
