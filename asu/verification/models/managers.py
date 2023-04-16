from datetime import timedelta
from typing import TYPE_CHECKING, Any, TypeVar

from django.conf import settings
from django.core import signing
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

if TYPE_CHECKING:
    from asu.verification.models import (  # noqa: F401
        EmailVerification,
        PasswordResetVerification,
        RegistrationVerification,
    )
    from asu.verification.models.base import ConsentVerification, Verification


V = TypeVar("V", bound="Verification")
CV = TypeVar("CV", bound="ConsentVerification")


class VerificationManager(models.Manager[V]):
    verify_period: int

    def verifiable(self) -> QuerySet[V]:
        max_verify_date = timezone.now() - timedelta(
            seconds=self.verify_period
        )
        return self.filter(
            date_verified__isnull=True,
            date_created__gt=max_verify_date,
            nulled_by__isnull=True,
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

    def get_with_consent(
        self, email: str, consent: str, **kwargs: Any
    ) -> CV | None:
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


class RegistrationVerificationManager(
    ConsentVerificationManager["RegistrationVerification"]
):
    verify_period = settings.REGISTRATION_VERIFY_PERIOD
    eligible_period = settings.REGISTRATION_REGISTER_PERIOD

    def eligible(self) -> QuerySet["RegistrationVerification"]:
        return super().eligible().filter(user__isnull=True)


class PasswordResetVerificationManager(
    ConsentVerificationManager["PasswordResetVerification"]
):
    verify_period = settings.PASSWORD_VERIFY_PERIOD
    eligible_period = settings.PASSWORD_RESET_PERIOD


class EmailVerificationManager(VerificationManager["EmailVerification"]):
    verify_period = settings.EMAIL_VERIFY_PERIOD

    def verifiable(self) -> QuerySet["EmailVerification"]:
        return super().verifiable().filter(user__isnull=False)
