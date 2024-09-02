from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Literal, TypedDict

from django.apps import apps
from django.conf import settings
from django.db import models, transaction
from django.db.models import Case, OuterRef, Q, QuerySet, When
from django.db.models.functions import JSONObject
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

if TYPE_CHECKING:
    from asu.auth.models import User
    from asu.messaging.models import Message

channel_layer = get_channel_layer()

# todo: juggle models around


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


class ConversationManager(models.Manager["Conversation"]):
    def annotate_last_message(
        self, queryset: QuerySet[Conversation]
    ) -> QuerySet[Conversation]:
        fields = (
            "id",
            "body",
            "sender_id",
            "has_receipt",
            "reply_to_id",
            "date_created",
        )
        mapping = dict(zip(fields, fields, strict=True))

        # todo requires optimization and possibly different serializer.
        # maybe we'll just append last event instead?
        messages = (
            apps.get_model("messaging.Message")
            .objects.filter(events__conversation=OuterRef("pk"))
            .order_by("-events__date_created")
            .values(data=JSONObject(**mapping))
        )
        return queryset.annotate(last_message=messages[:1])


class Conversation(models.Model):
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="conversations",
        verbose_name=_("holder"),
        help_text=_(
            "In private conversations, this field holds one of the participants."
            " In group conversations, this field holds the creator of the conversation."
        ),
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="targeted_conversations",
        verbose_name=_("target"),
    )
    is_group = models.BooleanField(_("group"), default=False)

    # Group-exclusive fields
    name = models.CharField(_("name"), max_length=100, blank=True)
    description = models.TextField(_("description"), blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("participants"),
        through=Participation,
        blank=True,
    )

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ConversationManager()

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        constraints = [
            models.UniqueConstraint(
                fields=["holder", "target"],
                condition=Q(is_group=False),
                name="unique_private_conversation",
            ),
            # todo separate these
            models.CheckConstraint(
                check=Case(
                    When(
                        is_group=False,
                        then=Q(holder__isnull=False) & Q(target__isnull=False),
                    ),
                    When(
                        is_group=True,
                        then=Q(holder__isnull=False) & Q(target__isnull=True),
                    ),
                    default=False,
                    output_field=models.BooleanField(),
                ),
                name="valid_private_conversation",
                violation_error_message=_(
                    "Private conversations must have valid holder and target fields."
                ),
            ),
            #         "Group conversations must have a valid name and holder,"
            #         " and the target must be null."
        ]
        indexes = [
            models.Index(fields=["date_modified"]),
        ]

    def __str__(self) -> str:
        return str(self.pk)


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
