from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils.html import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from zeynep import mailing
from zeynep.verification.models.base import ConsentVerification
from zeynep.verification.models.managers import RegistrationVerificationManager

app_config = apps.get_app_config("verification")


class RegistrationVerification(ConsentVerification):
    ELIGIBLE_PERIOD = app_config.REGISTRATION_REGISTER_PERIOD

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = RegistrationVerificationManager()

    class Meta(ConsentVerification.Meta):
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")

    @property
    def is_eligible(self):
        if self.user is not None:
            return False
        return super().is_eligible

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
