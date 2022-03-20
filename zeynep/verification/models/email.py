from django.utils.translation import gettext_lazy as _

from zeynep.utils import messages
from zeynep.verification.models.base import Verification
from zeynep.verification.models.managers import EmailVerificationManager


class EmailVerification(Verification):
    class Meta(Verification.Meta):
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    objects = EmailVerificationManager()

    MESSAGES = messages.email_verification
