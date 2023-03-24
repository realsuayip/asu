from django.db import models
from django.utils.translation import gettext_lazy as _

from oauth2_provider.models import (
    AbstractApplication,
    ApplicationManager as BaseApplicationManager,
)

from asu.utils.templatetags import get_variable


class ApplicationManager(BaseApplicationManager):
    def get_default(self):
        # Figure out the default application, this is application is
        # used to programmatically issue tokens, outside the oauth
        # flows. For example, immediately after the registration.
        default_client = get_variable("db.DEFAULT_OAUTH_CLIENT")
        apps = self.filter(
            client_id=default_client,
            is_first_party=True,
            skip_authorization=True,
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )
        return apps.get()


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
