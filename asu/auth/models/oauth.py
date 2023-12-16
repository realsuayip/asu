from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from oauth2_provider.models import AbstractApplication

from asu.models import ProjectVariable


class ApplicationManager(models.Manager["Application"]):
    def get_default(self) -> Application:
        # Figure out the default application, this is application is
        # used to programmatically issue tokens, outside the oauth
        # flows. For example, immediately after the registration.
        client = ProjectVariable.objects.get_value(name="db.DEFAULT_OAUTH_CLIENT")
        apps = self.filter(
            client_id=client,
            is_first_party=True,
            skip_authorization=True,
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )
        return apps.get()

    def get_by_natural_key(self, client_id: str) -> Application:  # pragma: no cover
        return self.get(client_id=client_id)


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

    class Meta:
        verbose_name = _("application")
        verbose_name_plural = _("applications")

    def natural_key(self) -> tuple[str]:  # pragma: no cover
        return (self.client_id,)
