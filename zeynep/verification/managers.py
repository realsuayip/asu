from django.db import models
from django.utils import timezone


class RegistrationVerificationManager(models.Manager):
    def eligible(self):
        period = self.model._meta.app_config.REGISTRATION_REGISTER_PERIOD
        max_verify_date = timezone.now() - timezone.timedelta(seconds=period)
        return self.filter(
            date_verified__isnull=False, date_verified__lt=max_verify_date
        )
