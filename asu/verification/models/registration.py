from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from asu.utils import messages
from asu.verification.models.base import ConsentVerification
from asu.verification.models.managers import RegistrationVerificationManager


class RegistrationVerification(ConsentVerification):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = RegistrationVerificationManager()

    ELIGIBLE_PERIOD = settings.REGISTRATION_REGISTER_PERIOD
    MESSAGES = messages.registration

    class Meta(ConsentVerification.Meta):
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")

    @property
    def is_eligible(self):
        if self.user is not None:
            return False
        return super().is_eligible
