from typing import ClassVar

from django.conf import settings
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from asu.core.utils import messages
from asu.verification.models.base import Verification, VerificationManager


class EmailVerificationManager(VerificationManager["EmailVerification"]):
    def verifiable(self) -> QuerySet[EmailVerification]:
        return super().verifiable().filter(user__isnull=False)


class EmailVerification(Verification):
    class Meta(Verification.Meta):
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    objects: ClassVar = EmailVerificationManager()

    VERIFY_PERIOD = settings.EMAIL_VERIFY_PERIOD
    EMAIL_MESSAGE = messages.email_verification
