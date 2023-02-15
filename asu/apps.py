from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class AsuConfig(AppConfig):
    name = "asu"
    verbose_name = pgettext_lazy("app name", "asu")
