from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class MessagingConfig(AppConfig):
    name = "asu.messaging"
    verbose_name = pgettext_lazy("app name", "Messaging")

    def ready(self) -> None:
        import asu.messaging.models.signals  # noqa: PLC0415, F401
