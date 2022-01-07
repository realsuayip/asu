from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class AuthConfig(AppConfig):
    name = "zeynep.auth"
    label = "zeynep_auth"
    verbose_name = pgettext_lazy("app name", "Auth")
