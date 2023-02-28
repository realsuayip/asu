from django.db import models
from django.utils.translation import gettext_lazy as _

from oauth2_provider.models import AbstractApplication, ApplicationManager


class Application(AbstractApplication):
    is_first_party = models.BooleanField(
        _("First party application"),
        help_text=_(
            "When activated, marks this application as first party,"
            " which exposes access to various internal APIs. ONLY use"
            " for trusted applications."
        ),
        default=False,
    )

    objects = ApplicationManager()

    class Meta(AbstractApplication.Meta):
        verbose_name = _("application")
        verbose_name_plural = _("applications")

    def natural_key(self):
        return (self.client_id,)
