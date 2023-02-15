from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class AuthConfig(AppConfig):
    name = "asu.auth"
    label = "account"
    verbose_name = pgettext_lazy("app name", "Auth")
