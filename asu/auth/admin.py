from django.contrib import admin
from django.contrib.auth import models as django_auth_models
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.utils.translation import gettext_lazy as _

import django_otp.plugins.otp_static.admin
import django_otp.plugins.otp_totp.admin
import oauth2_provider.admin
from django_otp.plugins.otp_static import models as static_models
from django_otp.plugins.otp_totp import models as totp_models
from oauth2_provider import models as oauth2_models

from asu.auth.models import (
    AccessToken,
    Grant,
    Group,
    Permission,
    RefreshToken,
    StaticDevice,
    TOTPDevice,
    User,
)

admin.site.unregister(django_auth_models.Group)

admin.site.unregister(oauth2_models.AccessToken)
admin.site.unregister(oauth2_models.RefreshToken)
admin.site.unregister(oauth2_models.Grant)
admin.site.unregister(oauth2_models.IDToken)

admin.site.unregister(static_models.StaticDevice)
admin.site.unregister(totp_models.TOTPDevice)


@admin.register(User)
class UserAdmin(BaseUserAdmin[User]):
    readonly_fields = (
        "is_frozen",
        "last_login",
        "created_at",
        "updated_at",
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
                    "created_at",
                    "updated_at",
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
    list_display = ("username", "email", "display_name", "created_at")
    search_fields = ("username", "email")
    ordering = ("-id",)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    ordering = ("-id",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin[Permission]):
    list_display = ("name", "codename", "content_type")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")
    ordering = ("-id",)


@admin.register(AccessToken)
class AccessTokenAdmin(oauth2_provider.admin.AccessTokenAdmin):
    pass


@admin.register(RefreshToken)
class RefreshTokenAdmin(oauth2_provider.admin.RefreshTokenAdmin):
    pass


@admin.register(Grant)
class GrantAdmin(oauth2_provider.admin.GrantAdmin):
    pass


@admin.register(StaticDevice)
class StaticDeviceAdmin(django_otp.plugins.otp_static.admin.StaticDeviceAdmin):
    pass


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(django_otp.plugins.otp_totp.admin.TOTPDeviceAdmin):
    pass
