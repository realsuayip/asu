from django.utils.html import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from zeynep import mailing
from zeynep.verification.models.base import Verification
from zeynep.verification.models.managers import EmailVerificationManager


class EmailVerification(Verification):
    class Meta(Verification.Meta):
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    objects = EmailVerificationManager()

    def send_email(self):
        title = gettext("Verify this email address")
        content = mark_safe(
            gettext(
                "To change your email, you need to enter the following"
                " code into the application:"
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
