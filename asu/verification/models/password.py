from django.conf import settings
from django.utils.translation import gettext_lazy as _

from asu.core.utils import messages
from asu.verification.models.base import ExtendedVerification


class PasswordResetVerification(ExtendedVerification):
    COMPLETE_TIMEOUT = settings.PASSWORD_RESET_COMPLETE_TIMEOUT
    VERIFY_TIMEOUT = settings.PASSWORD_RESET_VERIFY_TIMEOUT
    EMAIL_MESSAGE = messages.PASSWORD_RESET

    class Meta(ExtendedVerification.Meta):
        verbose_name = _("password reset verification")
        verbose_name_plural = _("password reset verifications")
