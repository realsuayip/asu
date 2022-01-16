import string

from django.conf import settings
from django.core.signing import TimestampSigner
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from zeynep.verification.managers import RegistrationVerificationManager


class RegistrationVerification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    email = models.EmailField(_("email"))
    code = models.CharField(_("code"), max_length=6)

    date_verified = models.DateTimeField(
        _("date verified"), null=True, blank=True
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = RegistrationVerificationManager()

    class Meta:
        verbose_name = _("registration verification")
        verbose_name_plural = _("registration verifications")

    def __str__(self):
        return "%s <#%s>" % (self.email, self.pk)

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.code = get_random_string(6, allowed_chars=string.digits)

        super().save(*args, **kwargs)

    def create_signature(self):
        assert self.is_eligible()

        signer = TimestampSigner()
        return signer.sign(self.pk)

    def is_eligible(self):
        """
        Can we create an account with this email?
        """
        if self.date_verified is None:
            return False

        period = self._meta.app_config.REGISTRATION_REGISTER_PERIOD
        delta = (timezone.now() - self.date_verified).total_seconds()
        return delta < period
