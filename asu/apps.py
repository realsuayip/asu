from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import pgettext_lazy

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

import asu.celery

ignore_logger("django.security.DisallowedHost")


class AsuConfig(AppConfig):
    name = "asu"
    verbose_name = pgettext_lazy("app name", "asu")

    def ready(self) -> None:
        if settings.SENTRY_ENABLED:
            sentry_sdk.init(  # pragma: no cover
                dsn=settings.SENTRY_DSN,
                environment=settings.PROJECT_ENVIRONMENT,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                integrations=[DjangoIntegration(), CeleryIntegration()],
                send_default_pii=True,
            )

        asu.celery.app.autodiscover_tasks(force=True)
