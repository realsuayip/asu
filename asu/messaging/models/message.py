from django.conf import settings
from django.db import models
from django.utils import dateformat
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from asu.messaging.models.managers import MessageManager

channel_layer = get_channel_layer()


class Message(models.Model):
    body = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    has_receipt = models.BooleanField(default=True)

    date_read = models.DateTimeField(_("date read"), null=True, blank=True)
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = MessageManager()

    @cached_property
    def sender_conversation(self):
        # Used in "MessageComposeSerializer" to retrieve related
        # conversation hyperlink.
        return self.conversations.only("pk").get(holder=self.sender)

    def websocket_send(self, target_conversation_id):
        group = "conversations_%s" % self.recipient_id
        event = {
            "type": "conversation.message",
            "conversation_id": target_conversation_id,
            "message_id": self.pk,
            "timestamp": dateformat.format(self.date_created, "U"),
        }
        async_to_sync(channel_layer.group_send)(group, event)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
