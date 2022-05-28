from django.apps import AppConfig
from django.utils.translation import pgettext_lazy


class MessagingConfig(AppConfig):
    name = "zeynep.messaging"
    verbose_name = pgettext_lazy("app name", "Messaging")
