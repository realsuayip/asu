from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from zeynep import mailing
from zeynep.verification.models.base import Verification
from zeynep.verification.models.managers import RegistrationVerificationManager


class RegistrationVerification(Verification):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = RegistrationVerificationManager()

    class Meta(Verification.Meta):
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")

    def __str__(self):
        return "%s <#%s>" % (self.email, self.pk)

    def create_consent(self):
        assert self.is_eligible

        signer = signing.TimestampSigner()
        return signer.sign(self.pk)

    @property
    def is_eligible(self):
        """
        Can we create an account with this email?
        """
        if self.date_verified is None:
            return False

        if self.user is not None:
            return False

        period = self._meta.app_config.REGISTRATION_REGISTER_PERIOD
        delta = (timezone.now() - self.date_verified).total_seconds()
        return delta < period

    def send_email(self):
        title = gettext("Verify your email for registration")
        content = mark_safe(
            gettext(
                "To continue for the registration process,"
                " you need to enter the following code into"
                " the application:"
                "<div class='code'><strong>%(code)s</strong></div>"
            )
            % {"code": self.code}
        )

        return mailing.send(
            "transactional",
            title=title,
            content=content,
            recipients=[self.email],
        )
