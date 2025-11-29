from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from asu.core.utils import messages
from asu.verification.models.base import ConsentVerification, ConsentVerificationManager


class RegistrationVerificationManager(
    ConsentVerificationManager["RegistrationVerification"]
):
    def eligible(self) -> QuerySet[RegistrationVerification]:
        return (
            super().eligible().filter(user__isnull=True)
        )  # todo maybe make this default if  user is always set after final step


class RegistrationVerification(ConsentVerification):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects: ClassVar = RegistrationVerificationManager()

    COMPLETE_PERIOD = settings.REGISTRATION_REGISTER_PERIOD
    VERIFY_PERIOD = settings.REGISTRATION_VERIFY_PERIOD
    EMAIL_MESSAGE = messages.registration

    class Meta(ConsentVerification.Meta):
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")

    @property
    def is_eligible(self) -> bool:
        if self.user is not None:
            return False
        return super().is_eligible
