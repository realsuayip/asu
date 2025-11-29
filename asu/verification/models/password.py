from django.conf import settings
from django.utils.translation import gettext_lazy as _

from asu.core.utils import messages
from asu.verification.models.base import ConsentVerification


class PasswordResetVerification(ConsentVerification):
    COMPLETE_PERIOD = settings.PASSWORD_RESET_PERIOD
    VERIFY_PERIOD = settings.PASSWORD_VERIFY_PERIOD
    EMAIL_MESSAGE = messages.password_reset

    class Meta(ConsentVerification.Meta):
        verbose_name = _("password reset verification")
        verbose_name_plural = _("password reset verifications")
