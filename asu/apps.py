from django.apps import AppConfig
from django.utils.translation import pgettext_lazy

import sentry_sdk
from envanter import env
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

import asu.celery

ignore_logger("django.security.DisallowedHost")


class AsuConfig(AppConfig):
    name = "asu"
    verbose_name = pgettext_lazy("app name", "asu")

    def ready(self) -> None:
        enabled = env.bool("SENTRY_ENABLED")

        if enabled:
            sentry_sdk.init(  # pragma: no cover
                dsn=env.str("SENTRY_DSN"),
                environment=env.str("SENTRY_ENVIRONMENT"),
                traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE"),
                integrations=[DjangoIntegration(), CeleryIntegration()],
                send_default_pii=True,
            )

        asu.celery.app.autodiscover_tasks(force=True)
