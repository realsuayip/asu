import string
import uuid

from django.conf import settings
from django.core import signing
from django.core.validators import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import classproperty
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _

from asu.utils import mailing


def code_validator(code):
    errors = []

    if len(code) < 6:
        errors.append(_("Ensure this field has at least 6 digits."))

    if not code.isdigit():
        errors.append(_("Ensure this field contains only digits."))

    raise ValidationError(errors)


class Verification(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    email = models.EmailField(_("email"), db_index=True)
    code = models.CharField(
        _("code"),
        max_length=6,
        validators=[code_validator],
    )

    # If the user successfully makes use of another verification object,
    # null remaining verification objects so that they couldn't be used
    # to repeat the related action. In a nutshell, this field is another
    # way of stating "is_expired".
    nulled_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        verbose_name=_("nulled by"),
        on_delete=models.SET_NULL,
    )

    date_verified = models.DateTimeField(
        _("date verified"),
        null=True,
        blank=True,
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    # Specifies a namedtuple (subject, body) to be used in send_mail.
    MESSAGES = None

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

    def null_others(self):
        queryset = self._meta.model.objects.verifiable()
        queryset.update(nulled_by=self)

    def send_email(self):
        title = self.MESSAGES.subject
        content = mark_safe(self.MESSAGES.body % {"code": self.code})
        return mailing.send(
            "transactional",
            title=title,
            content=content,
            recipients=[self.email],
        )


class ConsentVerification(Verification):
    date_completed = models.DateTimeField(
        _("date completed"),
        null=True,
        blank=True,
    )

    ELIGIBLE_PERIOD: int

    class Meta(Verification.Meta):
        abstract = True

    def __str__(self):
        return "%s <#%s>" % (self.email, self.pk)

    @classproperty
    def ident(cls):
        return "consent_" + cls._meta.model_name

    def create_consent(self):
        assert self.is_eligible

        obj = {"ident": self.ident, "value": self.uuid.hex}
        signer = signing.TimestampSigner()
        return signer.sign_object(obj)

    @property
    def is_eligible(self):
        if (self.date_verified is None) or self.date_completed:
            return False

        period = self.ELIGIBLE_PERIOD
        delta = (timezone.now() - self.date_verified).total_seconds()
        return delta < period

    def null_others(self):
        queryset = self._meta.model.objects.eligible()
        queryset.update(nulled_by=self)
