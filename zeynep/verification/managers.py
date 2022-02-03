from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class RegistrationVerificationManager(models.Manager):
    @cached_property
    def app_config(self):
        return self.model._meta.app_config  # noqa

    def eligible(self):
        period = self.app_config.REGISTRATION_REGISTER_PERIOD
        max_register_date = timezone.now() - timezone.timedelta(seconds=period)
        return self.filter(
            user__isnull=True,
            date_verified__isnull=False,
            date_verified__gt=max_register_date,
        )

    def verifiable(self):
        period = self.app_config.REGISTRATION_VERIFY_PERIOD
        max_verify_date = timezone.now() - timezone.timedelta(seconds=period)
        return self.filter(
            date_verified__isnull=True,
            date_created__gt=max_verify_date,
        )

    def get_with_consent(self, email, consent):
        """
        Check consent, if valid, fetch related RegistrationVerification
        object and return it, else return None. 'email' should be normalized.
        """
        signer = signing.TimestampSigner()
        max_age = self.app_config.REGISTRATION_REGISTER_PERIOD

        try:
            value = signer.unsign(consent, max_age=max_age)
        except (signing.BadSignature, signing.SignatureExpired):
            return None

        try:
            return self.eligible().get(pk=int(value), email=email)
        except self.model.DoesNotExist:
            return None
