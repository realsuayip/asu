from django.conf import settings
from django.utils.translation import gettext_lazy as _

from zaida.utils import messages
from zaida.verification.models.base import ConsentVerification
from zaida.verification.models.managers import PasswordResetVerificationManager


class PasswordResetVerification(ConsentVerification):
    objects = PasswordResetVerificationManager()

    ELIGIBLE_PERIOD = settings.PASSWORD_RESET_PERIOD
    MESSAGES = messages.password_reset

    class Meta(ConsentVerification.Meta):
        verbose_name = _("password reset verification")
        verbose_name_plural = _("password reset verifications")
