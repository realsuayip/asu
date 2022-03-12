from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone


class VerificationManager(models.Manager):
    verify_period: int

    def verifiable(self):
        max_verify_date = timezone.now() - timezone.timedelta(
            seconds=self.verify_period
        )
        return self.filter(
            date_verified__isnull=True,
            date_created__gt=max_verify_date,
            nulled_by__isnull=True,
        )


class ConsentVerificationManager(VerificationManager):
    eligible_period: int

    def eligible(self):
        period = self.eligible_period
        max_register_date = timezone.now() - timezone.timedelta(seconds=period)
        return self.filter(
            date_verified__isnull=False,
            date_completed__isnull=True,
            date_verified__gt=max_register_date,
            nulled_by__isnull=True,
        )

    def get_with_consent(self, email, consent, **kwargs):
        """
        Check consent, if valid, fetch related RegistrationVerification
        object and return it, else return None. 'email' should be normalized.
        """
        signer = signing.TimestampSigner()
        max_age = self.eligible_period

        try:
            value = signer.unsign(consent, max_age=max_age)
        except (signing.BadSignature, signing.SignatureExpired):
            return None

        try:
            return self.eligible().get(pk=int(value), email=email, **kwargs)
        except self.model.DoesNotExist:
            return None


class RegistrationVerificationManager(ConsentVerificationManager):
    verify_period = settings.REGISTRATION_VERIFY_PERIOD
    eligible_period = settings.REGISTRATION_REGISTER_PERIOD

    def eligible(self):
        return super().eligible().filter(user__isnull=True)


class PasswordResetVerificationManager(ConsentVerificationManager):
    verify_period = settings.PASSWORD_VERIFY_PERIOD
    eligible_period = settings.PASSWORD_RESET_PERIOD


class EmailVerificationManager(VerificationManager):
    verify_period = settings.EMAIL_VERIFY_PERIOD

    def verifiable(self):
        return super().verifiable().filter(user__isnull=False)
