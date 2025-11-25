import string
import uuid
from datetime import timedelta
from typing import Any, TypeVar

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.db.models.expressions import DatabaseDefault
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _

from asu.core.models.base import Base
from asu.core.utils import mailing
from asu.core.utils.messages import EmailMessage

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
            verified_at__isnull=True,
            created_at__gt=max_verify_date,
            nulled_by__isnull=True,
        )


class Verification(Base):
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

    verified_at = models.DateTimeField(
        _("date verified"),
        null=True,
        blank=True,
    )

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
        created = isinstance(self.pk, DatabaseDefault)

        if created:
            self.code = get_random_string(6, allowed_chars=string.digits)

        super().save(*args, **kwargs)

    def null_others(self) -> None:
        queryset = type(self).objects.verifiable()
        queryset.update(nulled_by=self)

    def send_email(self) -> int:
        title, content = self.MESSAGES.subject, self.MESSAGES.body
        return mailing.send(
            "code",
            title=title,
            content=content,
            recipients=[self.email],
            context={"code": self.code},
        )


class ConsentVerificationManager(VerificationManager[CV]):
    eligible_period: int

    def eligible(self) -> QuerySet[CV]:
        period = self.eligible_period
        max_register_date = timezone.now() - timedelta(seconds=period)
        return self.filter(
            verified_at__isnull=False,
            completed_at__isnull=True,
            verified_at__gt=max_register_date,
            nulled_by__isnull=True,
        )

    def get_with_consent(self, email: str, consent: str, **kwargs: Any) -> CV | None:
        """
        Check consent, if valid, fetch related RegistrationVerification
        object and return it, else return None. 'email' should be normalized.
        """
        signer = signing.TimestampSigner(salt=self.model.salt)
        try:
            value = signer.unsign(consent, max_age=self.eligible_period)
            return self.eligible().get(uuid=value, email__iexact=email, **kwargs)
        except (signing.BadSignature, self.model.DoesNotExist):
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

    completed_at = models.DateTimeField(
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
    def salt(cls) -> str:  # noqa: N805
        return "consent_" + cls._meta.db_table

    def create_consent(self) -> str:
        assert self.is_eligible
        signer = signing.TimestampSigner(salt=self.salt)
        return signer.sign(self.uuid.hex)

    @property
    def is_eligible(self) -> bool:
        if (self.verified_at is None) or self.completed_at:
            return False

        period = self.ELIGIBLE_PERIOD
        delta = (timezone.now() - self.verified_at).total_seconds()
        return delta < period

    def null_others(self) -> None:
        queryset = type(self).objects.eligible()
        queryset.update(nulled_by=self)
