import string
import uuid
from collections.abc import Iterable
from datetime import timedelta
from functools import partial
from typing import ClassVar, Self

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import OperationalError, models, transaction
from django.db.models import Q, QuerySet
from django.db.models.functions import Length, Now
from django.db.models.lookups import Exact
from django.utils import timezone
from django.utils.crypto import constant_time_compare, get_random_string, salted_hmac
from django.utils.translation import gettext_lazy as _

from asu.auth.models import User
from asu.core.models.base import Base, BaseManager
from asu.core.utils import mailing
from asu.core.utils.messages import EmailMessage

code_validator = RegexValidator(
    regex=r"^\d{6}$",
    message=_("Please enter a valid code."),
)


def get_code_hash(
    *,
    pk: uuid.UUID,
    code: str,
) -> str:
    return salted_hmac(
        key_salt=pk.bytes,
        value=code,
        secret=settings.VERIFICATION_SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


class VerificationManager[T: Verification](BaseManager[T]):
    @transaction.atomic(durable=True)
    def start(
        self,
        *,
        pk: uuid.UUID,
        email: str,
        user: User | None = None,
    ) -> None:
        code = get_random_string(6, allowed_chars=string.digits)
        code_hash = get_code_hash(pk=pk, code=code)
        verification = self.create(
            pk=pk,
            email=email,
            user=user,
            code_hash=code_hash,
        )
        send_email = partial(verification.send_email, code=code)
        transaction.on_commit(send_email)

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
        on_delete=models.DB_CASCADE,
    )
    email = models.EmailField(_("email"))
    code_hash = models.CharField(_("code hash"))
    nulled_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        verbose_name=_("nulled by"),
        on_delete=models.DB_SET_NULL,
    )
    verified_at = models.DateTimeField(_("date verified"), null=True, blank=True)

    VERIFY_TIMEOUT: int
    EMAIL_MESSAGE: EmailMessage

    objects: ClassVar[VerificationManager[Self]] = VerificationManager()

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                name="%(class)s_code_hash_length",
                condition=Exact(Length("code_hash"), 64),
            )
        ]

    def verify_code(self, *, code: str) -> bool:
        code_hash = get_code_hash(pk=self.pk, code=code)
        return constant_time_compare(self.code_hash, code_hash)

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

    def send_email(
        self,
        *,
        code: str,
    ) -> int:
        title, content = self.EMAIL_MESSAGE.subject, self.EMAIL_MESSAGE.body
        return mailing.send(
            "code.html",
            title=title,
            content=content,
            recipients=[self.email],
            context={"code": code},
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
