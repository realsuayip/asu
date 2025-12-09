import string
import uuid
from collections.abc import Iterable
from datetime import timedelta
from functools import partial
from typing import ClassVar, Self

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import OperationalError, models
from django.db.models import Q, QuerySet
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

    def lock_verifiable(self, *, condition: Q, nowait: bool = False) -> list[uuid.UUID]:
        return list(
            self.verifiable()
            .filter(condition)
            .values_list("id", flat=True)
            .select_for_update(nowait=nowait)
        )


class Verification(Base):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
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

    def null_others(self, *, locked: Iterable[uuid.UUID]) -> None:
        # If the user successfully makes use of another verification object,
        # null outstanding verification objects so that they couldn't be used
        # to repeat the related action.
        others = [pk for pk in locked if pk != self.pk]
        if not others:
            return
        type(self).objects.filter(
            pk__in=others,
            nulled_by__isnull=True,
        ).update(nulled_by=self, updated_at=Now())

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

    def lock_eligible(self, *, condition: Q) -> list[uuid.UUID]:
        try:
            return list(
                self.eligible()
                .filter(condition)
                .values_list("id", flat=True)
                .select_for_update(nowait=True)
            )
        except OperationalError:
            return []


class ExtendedVerification(Verification):
    completed_at = models.DateTimeField(_("date completed"), null=True, blank=True)

    COMPLETE_TIMEOUT: int

    objects: ClassVar[ExtendedVerificationManager[Self]] = ExtendedVerificationManager()

    class Meta(Verification.Meta):
        abstract = True

    def complete(self, *, lock_query: Q, **attrs: object) -> bool:
        klass = type(self)
        verifiable, eligible = (
            klass.objects.lock_verifiable(condition=lock_query),
            klass.objects.lock_eligible(condition=lock_query),
        )
        if self.pk not in eligible:
            return False
        self.completed_at = Now()
        for name, value in attrs.items():
            setattr(self, name, value)
        self.save(update_fields=[*attrs, "completed_at", "updated_at"])
        self.null_others(locked=verifiable + eligible)
        return True
