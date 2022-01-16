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
