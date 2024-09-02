from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Literal, TypedDict

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from asu.messaging.models.conversation import Conversation
from asu.messaging.models.request import ConversationRequest

if TYPE_CHECKING:
    from asu.auth.models import User
    from asu.messaging.models.message import Message

channel_layer = get_channel_layer()


class MessageEvent(TypedDict):
    id: int
    conversation_id: int
    type: Literal["conversation.message"]
    timestamp: str


class EventManager(models.Manager["Event"]):
    def dispatch(self, message: Message, recipient: User) -> Event:
        sender = message.sender

        # If conversation objects between these two people are not created,
        # create them. Otherwise, fetch their ID to perform related assignments.
        holder, _ = sender.conversations.get_or_create(target=recipient, is_group=False)
        target, _ = recipient.conversations.get_or_create(target=sender, is_group=False)

        # Create a conversation request if not exists. This way users have the
        # ability to see which conversations are newly requested. Requests are
        # automatically accepted in case recipient follows the sender.
        request, _ = ConversationRequest.objects.compose(sender, recipient)

        if (not request.is_accepted) and message.has_receipt:
            # Disable read receipts (regardless of user preference) in case
            # the conversation is yet to be accepted.
            message.has_receipt = False
            message.save(update_fields=["has_receipt"])

        attrs = {
            "message": message,
            "type": Event.Kind.MESSAGE,
            "date_created": message.date_created,
        }
        instance, _ = events = (
            Event.objects.create(conversation=holder, **attrs),
            Event.objects.create(conversation=target, **attrs),
        )
        # Update modification timestamps for related conversations so that when
        # ordering by modified, conversations with recent activity rise to top.
        Conversation.objects.filter(pk__in=[holder.pk, target.pk]).update(
            date_modified=timezone.now()
        )
        # Relay events via WebSocket.
        for event in events:
            relay = partial(event.websocket_send, target.pk)
            transaction.on_commit(relay)
        return instance


class Event(models.Model):
    class Kind(models.TextChoices):
        # todo: private msg vs group msg distinction
        # should be made or not, and how?
        MESSAGE = "message", _("message")

    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.CASCADE,
        verbose_name=_("conversation"),
        related_name="events",
    )
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        verbose_name=_("message"),
        null=True,
        blank=True,
        related_name="events",
    )
    type = models.CharField(
        _("type"),
        max_length=10,
        choices=Kind.choices,
    )

    date_created = models.DateTimeField(
        _("date created"),
        default=timezone.now,
        editable=False,
    )

    objects = EventManager()

    class Meta:
        verbose_name = _("conversation event")
        verbose_name_plural = _("conversation events")
        constraints = [
            # todo make this index also independent of condition
            models.UniqueConstraint(
                condition=Q(type="message"),
                fields=["conversation", "message"],
                name="unique_conversation_message",
            )
        ]

    def __str__(self) -> str:
        return str(self.pk)

    def websocket_send(self, target_conversation_id: int) -> None:
        send = async_to_sync(channel_layer.group_send)
        if self.conversation.is_group:
            pass
        else:
            group = "conversations_%s" % self.conversation.target_id
            event = MessageEvent(
                id=self.pk,
                conversation_id=target_conversation_id,
                type="conversation.message",
                timestamp=self.date_created.isoformat()[:-6] + "Z",
            )
            send(group, event)
