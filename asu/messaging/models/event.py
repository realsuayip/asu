from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from asu.messaging.models.conversation import Conversation
from asu.messaging.models.message import Message
from asu.messaging.models.participation import Participation
from asu.messaging.models.request import ConversationRequest

if TYPE_CHECKING:
    from asu.auth.models import User


channel_layer = get_channel_layer()


class WebsocketEvent(TypedDict):
    id: int
    conversation_id: int
    type: Literal["conversation.message"]
    timestamp: str


class EventManager(models.Manager["Event"]):
    def dispatch(
        self, message: Message, recipient: User, reply_to_id: int | None
    ) -> Event:
        sender = message.sender

        # If conversation objects between these two people are not created,
        # create them. Otherwise, fetch their ID to perform related assignments.
        holder, _ = sender.conversations.get_or_create(target=recipient, is_group=False)
        target, _ = recipient.conversations.get_or_create(target=sender, is_group=False)

        # Create a conversation request if not exists. This way users have the
        # ability to see which conversations are newly requested. Requests are
        # automatically accepted in case recipient follows the sender.
        request, _ = ConversationRequest.objects.compose(sender, recipient)

        # Set `reply_to` field, making sure it is a reply to a valid message
        # in the conversation.
        updates = set()
        if reply_to_id is not None:
            valid_reply_to = Message.objects.filter(
                pk=reply_to_id, events__conversation__in=(holder, target)
            ).exists()
            if valid_reply_to:
                message.reply_to_id = reply_to_id
                updates.add("reply_to_id")

        if (not request.is_accepted) and message.has_receipt:
            # Disable read receipts (regardless of user preference) in case
            # the conversation is yet to be accepted.
            message.has_receipt = False
            updates.add("has_receipt")

        if updates:
            message.save(update_fields=updates)

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
        Conversation.objects.filter(pk__in=(holder.pk, target.pk)).update(
            date_modified=timezone.now()
        )
        # Relay events via WebSocket.
        for event in events:
            transaction.on_commit(event.websocket_send)
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

    def timestamp(self) -> str:
        return serializers.DateTimeField().to_representation(self.date_created)

    def as_websocket_event(self) -> WebsocketEvent:
        # todo this will change depending on content type
        return WebsocketEvent(
            id=self.pk,
            conversation_id=self.conversation_id,
            type="conversation.message",
            timestamp=self.timestamp(),
        )

    @staticmethod
    def get_group(user_id: int) -> str:
        return "conversations_%s" % user_id

    def websocket_send(self) -> None:
        # todo testme
        send, event, conversation = (
            async_to_sync(channel_layer.group_send),
            self.as_websocket_event(),
            self.conversation,
        )
        if conversation.is_group:
            # todo: might get more complicated than that
            recipients = (
                Participation.objects.filter(conversation=conversation)
                .values_list("user_id", flat=True)
                .iterator()
            )
            for recipient in recipients:
                send(self.get_group(recipient), event)
        else:
            assert conversation.holder_id
            send(self.get_group(conversation.holder_id), event)
