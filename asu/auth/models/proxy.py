import django.contrib.auth.models

import django_otp.plugins.otp_static.models
import django_otp.plugins.otp_totp.models
import oauth2_provider.models


class Group(django.contrib.auth.models.Group):
    class Meta:
        proxy = True


class Permission(django.contrib.auth.models.Permission):
    class Meta:
        proxy = True


class AccessToken(oauth2_provider.models.AccessToken):
    class Meta:
        proxy = True


class RefreshToken(oauth2_provider.models.RefreshToken):
    class Meta:
        proxy = True


class Grant(oauth2_provider.models.Grant):
    class Meta:
        proxy = True


class StaticDevice(django_otp.plugins.otp_static.models.StaticDevice):
    class Meta:
        proxy = True


class TOTPDevice(django_otp.plugins.otp_totp.models.TOTPDevice):
    class Meta:
        proxy = True
