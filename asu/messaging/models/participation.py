from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Participation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        related_name="+",
    )
    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.CASCADE,
        verbose_name=_("conversation"),
        related_name="+",
    )

    class Meta:
        verbose_name = _("participation")
        verbose_name_plural = _("participations")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "conversation"],
                name="unique_participation",
            )
        ]

    def __str__(self) -> str:
        return str(self.pk)
