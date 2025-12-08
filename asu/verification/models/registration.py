from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.db.models.functions import Upper
from django.utils.translation import gettext_lazy as _

from asu.core.utils import messages
from asu.verification.models.base import (
    ExtendedVerification,
    ExtendedVerificationManager,
)


class RegistrationVerificationManager(
    ExtendedVerificationManager["RegistrationVerification"]
):
    def eligible(self) -> QuerySet[RegistrationVerification]:
        return super().eligible().filter(user__isnull=True)


class RegistrationVerification(ExtendedVerification):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects: ClassVar = RegistrationVerificationManager()

    VERIFY_TIMEOUT = settings.REGISTRATION_VERIFY_TIMEOUT
    COMPLETE_TIMEOUT = settings.REGISTRATION_COMPLETE_TIMEOUT
    EMAIL_MESSAGE = messages.REGISTRATION_VERIFICATION

    class Meta(ExtendedVerification.Meta):
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")
        indexes = [
            models.Index(
                Upper("email"),
                name="registration_verification_email_idx",
            )
        ]
