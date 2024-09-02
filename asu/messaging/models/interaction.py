from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Interaction(models.Model):
    # todo add jsonfield to hold additional data related to event
    class Kind(models.TextChoices):
        READ = "read", _("read")
        REACT = "react", _("react")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        related_name="interactions",
    )
    event = models.ForeignKey(
        "messaging.Event",
        on_delete=models.CASCADE,
        verbose_name=_("event"),
        related_name="interactions",
    )
    type = models.CharField(
        _("type"),
        max_length=10,
        choices=Kind.choices,
    )

    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        verbose_name = _("interaction")
        verbose_name_plural = _("interactions")

    def __str__(self) -> str:
        return str(self.pk)
