from django.apps import apps
from django.utils.html import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from zeynep import mailing
from zeynep.verification.models.base import ConsentVerification
from zeynep.verification.models.managers import (
    PasswordResetVerificationManager,
)

app_config = apps.get_app_config("verification")


class PasswordResetVerification(ConsentVerification):
    ELIGIBLE_PERIOD = app_config.PASSWORD_RESET_PERIOD

    objects = PasswordResetVerificationManager()

    class Meta(ConsentVerification.Meta):
        verbose_name = _("password reset verification")
        verbose_name_plural = _("password reset verifications")

    def send_email(self):
        title = gettext("Verify your email to reset your password")
        content = mark_safe(
            gettext(
                "To continue for the password reset process,"
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
