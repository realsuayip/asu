from django.conf import settings
from django.utils.translation import gettext_lazy as _

from asu.utils import messages
from asu.verification.models.base import ConsentVerification, ConsentVerificationManager


class PasswordResetVerificationManager(
    ConsentVerificationManager["PasswordResetVerification"]
):
    verify_period = settings.PASSWORD_VERIFY_PERIOD
    eligible_period = settings.PASSWORD_RESET_PERIOD


class PasswordResetVerification(ConsentVerification):
    objects = PasswordResetVerificationManager()

    ELIGIBLE_PERIOD = settings.PASSWORD_RESET_PERIOD
    MESSAGES = messages.password_reset

    class Meta(ConsentVerification.Meta):
        verbose_name = _("password reset verification")
        verbose_name_plural = _("password reset verifications")
