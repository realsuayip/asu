import string

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from zeynep import mailing
from zeynep.verification.managers import RegistrationVerificationManager
from zeynep.verification.models.base import code_validator


class RegistrationVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    email = models.EmailField(_("email"))
    code = models.CharField(
        _("code"), max_length=6, validators=[code_validator]
    )

    date_verified = models.DateTimeField(
        _("date verified"), null=True, blank=True
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = RegistrationVerificationManager()

    class Meta:
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")
        constraints = [
            models.UniqueConstraint(
                fields=["email", "code"], name="unique_email_and_code"
            )
        ]

    def __str__(self):
        return "%s <#%s>" % (self.email, self.pk)

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.code = get_random_string(6, allowed_chars=string.digits)

        super().save(*args, **kwargs)

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
