from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Interaction(models.Model):
    # todo add jsonfield to hold additional data related to event
    # todo save read events for each individual message
    class Kind(models.TextChoices):
        READ = "read", _("read")
        REACT = "react", _("react")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        related_name="interactions",
    )
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        verbose_name=_("message"),
        related_name="interactions",
    )
    type = models.CharField(
        _("type"),
        max_length=10,
        choices=Kind.choices,
    )

    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        # todo some kind of idx(user,event,type)
        verbose_name = _("interaction")
        verbose_name_plural = _("interactions")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "message"],
                condition=Q(type="read"),
                name="unique_read_interaction",
            ),
        ]

    def __str__(self) -> str:
        return str(self.pk)
