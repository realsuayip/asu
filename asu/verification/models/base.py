import string
import uuid
from datetime import timedelta
from typing import Any, TypeVar

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import classproperty
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from asu.utils import mailing
from asu.utils.messages import EmailMessage

V = TypeVar("V", bound="Verification")
CV = TypeVar("CV", bound="ConsentVerification")


def code_validator(code: str) -> None:
    errors = []

    if len(code) < 6:
        errors.append(_("Ensure this field has at least 6 digits."))

    if not code.isdigit():
        errors.append(_("Ensure this field contains only digits."))

    raise ValidationError(errors)


class VerificationManager(models.Manager[V]):
    verify_period: int

    def verifiable(self) -> QuerySet[V]:
        max_verify_date = timezone.now() - timedelta(seconds=self.verify_period)
        return self.filter(
            date_verified__isnull=True,
            date_created__gt=max_verify_date,
            nulled_by__isnull=True,
        )


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
    MESSAGES: EmailMessage

    objects: Any = VerificationManager()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["email", "code"],
                name="%(class)s_unique_email_and_code",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        created = self.pk is None

        if created:
            self.code = get_random_string(6, allowed_chars=string.digits)

        super().save(*args, **kwargs)

    def null_others(self) -> None:
        queryset = type(self).objects.verifiable()
        queryset.update(nulled_by=self)

    def send_email(self) -> int:
        title = self.MESSAGES.subject
        content = mark_safe(self.MESSAGES.body % {"code": self.code})
        return mailing.send(
            "transactional",
            title=title,
            content=content,
            recipients=[self.email],
        )


class ConsentVerificationManager(VerificationManager[CV]):
    eligible_period: int

    def eligible(self) -> QuerySet[CV]:
        period = self.eligible_period
        max_register_date = timezone.now() - timedelta(seconds=period)
        return self.filter(
            date_verified__isnull=False,
            date_completed__isnull=True,
            date_verified__gt=max_register_date,
            nulled_by__isnull=True,
        )

    def get_with_consent(self, email: str, consent: str, **kwargs: Any) -> CV | None:
        """
        Check consent, if valid, fetch related RegistrationVerification
        object and return it, else return None. 'email' should be normalized.
        """
        signer = signing.TimestampSigner()
        try:
            obj = signer.unsign_object(consent, max_age=self.eligible_period)
            ident, value = obj.get("ident"), obj.get("value")
            if (not value) or (not ident) or ident != self.model.ident:
                raise signing.BadSignature
            return self.eligible().get(uuid=value, email=email, **kwargs)
        except (
            signing.BadSignature,
            signing.SignatureExpired,
            self.model.DoesNotExist,
        ):
            return None


class ConsentVerification(Verification):
    """
    A consent is a secret string that acts as the proof of verification
    for given email. In this case, it is a signed string that contains
    the 'uuid' of an instance of this model.

    Consent string is useful when the verification involves an interim
    step. For example, instead of taking all user information during the
    registration flow, we only ask for the email first.

    If the user verifies the email, a consent is issued so that we know
    that email is good in subsequent request, which will contain all the
    user information [along with consent].

    The consent string is signed, however it is not necessary, any
    string that identifies the consent verification object in the
    database could be returned (provided that it is not easy to guess).

    The comment below dwells on why consent is signed. Do not read it.
    ~~~~~~~~~~~

    Initially there was no 'uuid' field; the string was signed so that
    the BIGINT 'id' field could not be enumerated. However, I realized
    that I was signing IDs across multiple flows, which could generate
    the same signed consents. This would again allow for enumeration;
    I needed to add some 'random' bit to the signed string, so, I added
    'uuid' field. I was already using the timestamp in the consent to
    check the age along with a pepper, so it was a quite stretch to say
    it could be enumerated...

    With the introduction of UUID, the reasoning for all the signing is
    not necessary since 'uuid' could not be enumerated. However, it
    still has a little benefit. I can discard invalid consents right
    away without having to check the database (for example in case of
    past age, or outright garbage consent information).
    """

    date_completed = models.DateTimeField(
        _("date completed"),
        null=True,
        blank=True,
    )

    ELIGIBLE_PERIOD: int

    objects: ConsentVerificationManager[Any] = ConsentVerificationManager()

    class Meta(Verification.Meta):
        abstract = True

    def __str__(self) -> str:
        return "%s <#%s>" % (self.email, self.pk)

    @classproperty
    def ident(cls) -> str:
        return "consent_" + cls._meta.db_table

    def create_consent(self) -> str:
        assert self.is_eligible

        obj = {"ident": self.ident, "value": self.uuid.hex}
        signer = signing.TimestampSigner()
        return signer.sign_object(obj)

    @property
    def is_eligible(self) -> bool:
        if (self.date_verified is None) or self.date_completed:
            return False

        period = self.ELIGIBLE_PERIOD
        delta = (timezone.now() - self.date_verified).total_seconds()
        return delta < period

    def null_others(self) -> None:
        queryset = type(self).objects.eligible()
        queryset.update(nulled_by=self)
