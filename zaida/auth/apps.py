from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class AuthConfig(AppConfig):
    name = "zaida.auth"
    label = "zaida_auth"
    verbose_name = pgettext_lazy("app name", "Auth")
