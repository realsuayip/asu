from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models, transaction
from django.utils import dateformat
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from asu.messaging.models import Conversation

if TYPE_CHECKING:
    from asu.auth.models import User


channel_layer = get_channel_layer()


class MessageManager(models.Manager["Message"]):
    @transaction.atomic
    def compose(self, sender: "User", recipient: "User", body: str) -> Message | None:
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

    @cached_property
    def sender_conversation(self) -> Conversation:
        # Used in "MessageComposeSerializer" to retrieve related
        # conversation hyperlink.
        return self.conversations.only("pk").get(holder=self.sender)

    def websocket_send(self, target_conversation_id: int) -> None:
        group = "conversations_%s" % self.recipient_id
        event = {
            "type": "conversation.message",
            "conversation_id": target_conversation_id,
            "message_id": self.pk,
            "timestamp": dateformat.format(self.date_created, "U"),
        }
        send = async_to_sync(channel_layer.group_send)  # type: ignore[no-untyped-call]
        send(group, event)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
