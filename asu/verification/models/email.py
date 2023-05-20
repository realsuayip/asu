from __future__ import annotations

from django.conf import settings
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from asu.utils import messages
from asu.verification.models.base import Verification, VerificationManager


class EmailVerificationManager(VerificationManager["EmailVerification"]):
    verify_period = settings.EMAIL_VERIFY_PERIOD

    def verifiable(self) -> QuerySet[EmailVerification]:
        return super().verifiable().filter(user__isnull=False)


class EmailVerification(Verification):
    class Meta(Verification.Meta):
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    objects = EmailVerificationManager()

    MESSAGES = messages.email_verification
