from django.apps import AppConfig
from django.utils.translation import pgettext_lazy

from zeynep.envparse import env


class VerificationConfig(AppConfig):
    name = "zeynep.verification"
    verbose_name = pgettext_lazy("app name", "Verification")

    REGISTRATION_VERIFY_PERIOD = env.int("REGISTRATION_VERIFY_PERIOD", 600)
    """
    Time allocated (seconds) to verify given email.
    """
    REGISTRATION_REGISTER_PERIOD = env.int("REGISTRATION_REGISTER_PERIOD", 600)
    """
    Time allocated (seconds) to register with the verified email.
    """
    EMAIL_VERIFY_PERIOD = env.int("EMAIL_VERIFY_PERIOD", 600)
    """
    Time allocated (seconds) to verify an email (for changing emails).
    """
