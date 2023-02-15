from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class MessagingConfig(AppConfig):
    name = "asu.messaging"
    verbose_name = pgettext_lazy("app name", "Messaging")

    def ready(self):
        import asu.messaging.models.signals  # noqa
