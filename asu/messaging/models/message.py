from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from asu.messaging.models import Conversation, Event

if TYPE_CHECKING:
    from asu.auth.models import User


class MessageManager(models.Manager["Message"]):
    @transaction.atomic
    def compose(
        self,
        sender: User,
        recipient: User | Conversation,
        body: str,
    ) -> Event | None:
        if isinstance(recipient, Conversation):
            # todo
            return None

        if not sender.can_send_message(recipient):
            return None

        has_receipt = sender.allows_receipts and recipient.allows_receipts
        message = self.create(sender=sender, body=body, has_receipt=has_receipt)
        return Event.objects.dispatch(message, recipient)


class Message(models.Model):
    body = models.TextField(_("body"))
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("sender"),
    )
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        verbose_name=_("reply to"),
        on_delete=models.SET_NULL,
    )

    has_receipt = models.BooleanField(_("has receipt"), default=True)

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = MessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self) -> str:
        return str(self.pk)
