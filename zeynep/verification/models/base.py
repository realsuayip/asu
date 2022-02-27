import string

from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.validators import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

app_config = apps.get_app_config("verification")


def code_validator(code):
    errors = []

    if len(code) < 6:
        errors.append(_("Ensure this field has at least 6 digits."))

    if not code.isdigit():
        errors.append(_("Ensure this field contains only digits."))

    raise ValidationError(errors)


class Verification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    email = models.EmailField(_("email"))
    code = models.CharField(
        _("code"),
        max_length=6,
        validators=[code_validator],
    )

    date_verified = models.DateTimeField(
        _("date verified"),
        null=True,
        blank=True,
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["email", "code"],
                name="%(class)s_unique_email_and_code",
            )
        ]

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.code = get_random_string(6, allowed_chars=string.digits)

        super().save(*args, **kwargs)


class ConsentVerification(Verification):
    ELIGIBLE_PERIOD: int

    class Meta(Verification.Meta):
        abstract = True

    def __str__(self):
        return "%s <#%s>" % (self.email, self.pk)

    def create_consent(self):
        assert self.is_eligible

        signer = signing.TimestampSigner()
        return signer.sign(self.pk)

    @property
    def is_eligible(self):
        if self.date_verified is None:
            return False

        period = self.ELIGIBLE_PERIOD
        delta = (timezone.now() - self.date_verified).total_seconds()
        return delta < period
