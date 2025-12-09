from typing import ClassVar

from django.conf import settings
from django.db import OperationalError, models
from django.db.models import Q, QuerySet
from django.db.models.functions import Now, Upper
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
        indexes = [
            models.Index(
                Upper("email"),
                name="email_verification_email_idx",
            )
        ]

    objects: ClassVar = EmailVerificationManager()

    VERIFY_TIMEOUT = settings.EMAIL_CHANGE_VERIFY_TIMEOUT
    EMAIL_MESSAGE = messages.EMAIL_CHANGE_VERIFICATION

    def complete(self) -> bool:
        try:
            locked = EmailVerification.objects.lock_verifiable(
                condition=Q(user_id=self.user_id) | Q(email__iexact=self.email),
                nowait=True,
            )
        except OperationalError:
            return False
        if self.pk not in locked:
            return False
        self.verified_at = Now()
        self.save(update_fields=["verified_at", "updated_at"])
        self.null_others(locked=locked)
        return True
