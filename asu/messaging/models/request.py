from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from asu.auth.models import User


class ConversationRequestManager(models.Manager["ConversationRequest"]):
    def compose(
        self, sender: User, recipient: User
    ) -> tuple[ConversationRequest, bool]:
        try:
            obj = self.get(
                Q(sender=sender, recipient=recipient)
                | Q(sender=recipient, recipient=sender)
            )
        except self.model.DoesNotExist:
            obj = None

        is_following = recipient.is_following(sender)

        if obj is not None:
            # A follow relation has been formed since the request
            # first created; automatically accept the request.
            if is_following and (obj.date_accepted is None):
                obj.date_accepted = timezone.now()
                obj.save(update_fields=["date_accepted", "date_modified"])
            return obj, False

        kwargs = {"sender": sender, "recipient": recipient}
        defaults = None

        if is_following:
            defaults = {"date_accepted": timezone.now()}
        return self.get_or_create(**kwargs, defaults=defaults)


class ConversationRequest(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("sender"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("recipient"),
    )

    date_accepted = models.DateTimeField(
        _("date_accepted"),
        null=True,
        blank=True,
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ConversationRequestManager()

    class Meta:
        verbose_name = _("conversation request")
        verbose_name_plural = _("conversation requests")
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "recipient"],
                name="unique_conversation_request",
            )
        ]

    def __str__(self) -> str:
        return str(self.pk)

    @property
    def is_accepted(self) -> bool:
        return self.date_accepted is not None
