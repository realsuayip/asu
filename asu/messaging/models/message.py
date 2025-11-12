from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

if TYPE_CHECKING:
    from asu.auth.models import User


channel_layer = get_channel_layer()


class MessageEvent(TypedDict):
    type: Literal["conversation.message"]
    conversation_id: int
    message_id: int
    timestamp: str


class MessageManager(models.Manager["Message"]):
    @transaction.atomic
    def compose(self, sender: User, recipient: User, body: str) -> Message | None:
        if not sender.can_send_message(recipient):
            return None

        has_receipt = sender.allows_receipts and recipient.allows_receipts
        return self.create(
            sender=sender,
            recipient=recipient,
            body=body,
            has_receipt=has_receipt,
        )


class Message(models.Model):
    body = models.TextField(_("body"))
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

    has_receipt = models.BooleanField(_("has receipt"), default=True)

    date_read = models.DateTimeField(_("date read"), null=True, blank=True)
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = MessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self) -> str:
        return str(self.pk)

    def websocket_send(self, target_conversation_id: int) -> None:
        group = "conversations_%s" % self.recipient_id
        event = MessageEvent(
            type="conversation.message",
            conversation_id=target_conversation_id,
            message_id=self.pk,
            timestamp=self.date_created.isoformat()[:-6] + "Z",
        )
        send = async_to_sync(channel_layer.group_send)
        send(group, event)
