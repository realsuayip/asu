from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class VerificationConfig(AppConfig):
    name = "asu.verification"
    verbose_name = pgettext_lazy("app name", "Verification")
