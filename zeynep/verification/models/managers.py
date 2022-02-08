from django.apps import apps
from django.core import signing
from django.db import models
from django.utils import timezone

app_config = apps.get_app_config("verification")


class VerificationManager(models.Manager):
    verify_period: int

    def verifiable(self):
        max_verify_date = timezone.now() - timezone.timedelta(
            seconds=self.verify_period
        )
        return self.filter(
            date_verified__isnull=True,
            date_created__gt=max_verify_date,
        )


class RegistrationVerificationManager(VerificationManager):
    verify_period = app_config.REGISTRATION_VERIFY_PERIOD

    def eligible(self):
        period = app_config.REGISTRATION_REGISTER_PERIOD
        max_register_date = timezone.now() - timezone.timedelta(seconds=period)
        return self.filter(
            user__isnull=True,
            date_verified__isnull=False,
            date_verified__gt=max_register_date,
        )

    def get_with_consent(self, email, consent):
        """
        Check consent, if valid, fetch related RegistrationVerification
        object and return it, else return None. 'email' should be normalized.
        """
        signer = signing.TimestampSigner()
        max_age = app_config.REGISTRATION_REGISTER_PERIOD

        try:
            value = signer.unsign(consent, max_age=max_age)
        except (signing.BadSignature, signing.SignatureExpired):
            return None

        try:
            return self.eligible().get(pk=int(value), email=email)
        except self.model.DoesNotExist:
            return None


class EmailVerificationManager(VerificationManager):
    verify_period = app_config.EMAIL_VERIFY_PERIOD

    def verifiable(self):
        return super().verifiable().filter(user__isnull=False)
