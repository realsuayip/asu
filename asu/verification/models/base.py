import string
from datetime import timedelta
from functools import partial
from typing import ClassVar, Self

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import QuerySet
from django.db.models.functions import Now
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from asu.core.models.base import Base
from asu.core.utils import mailing
from asu.core.utils.messages import EmailMessage

code_validator = RegexValidator(
    regex=r"^\d{6}$",
    message=_("Please enter a valid code."),
)
generate_random_code = partial(get_random_string, length=6, allowed_chars=string.digits)


class VerificationManager[T: Verification](models.Manager[T]):
    def verifiable(self) -> QuerySet[T]:
        timeout = self.model.VERIFY_TIMEOUT
        min_created_at = timezone.now() - timedelta(seconds=timeout)
        return self.filter(
            created_at__gt=min_created_at,
            verified_at__isnull=True,
            nulled_by__isnull=True,
        )


class Verification(Base):
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
        default=generate_random_code,
    )
    nulled_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        verbose_name=_("nulled by"),
        on_delete=models.SET_NULL,
    )
    verified_at = models.DateTimeField(_("date verified"), null=True, blank=True)

    VERIFY_TIMEOUT: int
    EMAIL_MESSAGE: EmailMessage

    objects: ClassVar[VerificationManager[Self]] = VerificationManager()

    class Meta:
        abstract = True

    def null_others(self) -> None:
        # If the user successfully makes use of another verification object,
        # null outstanding verification objects so that they couldn't be used
        # to repeat the related action.
        queryset = type(self).objects.verifiable()
        queryset.update(nulled_by=self, updated_at=Now())

    def send_email(self) -> int:
        title, content = self.EMAIL_MESSAGE.subject, self.EMAIL_MESSAGE.body
        return mailing.send(
            "code",
            title=title,
            content=content,
            recipients=[self.email],
            context={"code": self.code},
        )


class ExtendedVerificationManager[T: ExtendedVerification](VerificationManager[T]):
    def eligible(self) -> QuerySet[T]:
        # If a verification object is in 'eligible' state, it can be used to
        # 'complete' the related action.
        timeout = self.model.COMPLETE_TIMEOUT
        min_verified_at = timezone.now() - timedelta(seconds=timeout)
        return self.filter(
            verified_at__gt=min_verified_at,
            completed_at__isnull=True,
            nulled_by__isnull=True,
        )


class ExtendedVerification(Verification):
    completed_at = models.DateTimeField(_("date completed"), null=True, blank=True)

    COMPLETE_TIMEOUT: int

    objects: ClassVar[ExtendedVerificationManager[Self]] = ExtendedVerificationManager()

    class Meta(Verification.Meta):
        abstract = True

    def null_others(self) -> None:
        super().null_others()
        queryset = type(self).objects.eligible()
        queryset.update(nulled_by=self, updated_at=Now())
