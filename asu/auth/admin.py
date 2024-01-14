from django.contrib import admin, auth
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.utils.translation import gettext_lazy as _

from asu.auth.models import Group, Permission, User

admin.site.unregister(auth.models.Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    readonly_fields = (
        "is_frozen",
        "last_login",
        "date_joined",
        "date_modified",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "username",
                    "display_name",
                    "description",
                    "website",
                    "gender",
                    "birth_date",
                    "profile_picture",
                )
            },
        ),
        (
            _("Preferences"),
            {
                "fields": (
                    "language",
                    "allows_receipts",
                    "allows_all_messages",
                    "is_private",
                    "is_frozen",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "date_modified",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
    list_display = ("username", "email", "display_name", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    ordering = ("-id",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "content_type")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")
    ordering = ("-id",)
