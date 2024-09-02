from __future__ import annotations

from typing import Any

from django.utils import timezone

from rest_framework import exceptions, serializers
from rest_framework.reverse import reverse

from drf_spectacular.utils import extend_schema_field

from asu.auth.serializers.user import UserPublicReadSerializer
from asu.messaging.models import Conversation, ConversationRequest, Event, Message


class MessageSerializer(serializers.ModelSerializer[Message]):
    source = serializers.SerializerMethodField()  # type: ignore[assignment]

    class Meta:
        model = Message
        fields = ("body", "source", "reply_to_id", "date_created")

    @extend_schema_field(serializers.ChoiceField(choices=["sent", "received"]))
    def get_source(self, message: Message) -> str:
        user = self.context["request"].user
        return "sent" if message.sender_id == user.pk else "received"


class MessageComposeSerializer(serializers.ModelSerializer[Event]):
    conversation = serializers.HyperlinkedRelatedField(  # type: ignore[var-annotated]
        read_only=True, view_name="api:messaging:conversation-detail"
    )
    url = serializers.SerializerMethodField()
    # todo make this polymorphic, cases: groupmsg, privmsg, groupjoin
    # todo: make a reusable helper that resolves polymorphic serialization
    content = MessageSerializer(read_only=True, source="message")
    body = serializers.CharField(write_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "type",
            "content",
            "body",
            "conversation",
            "date_created",
            "url",
        )
        extra_kwargs = {"type": {"read_only": True}}

    @extend_schema_field(serializers.URLField)
    def get_url(self, obj: Event) -> str:
        return reverse(
            "api:messaging:message-detail",
            kwargs={"pk": obj.pk, "conversation_pk": obj.conversation_id},
            request=self.context["request"],
        )

    def create(self, validated_data: dict[str, Any]) -> Event:
        sender, recipient, body = (
            self.context["request"].user,
            self.context["recipient"],
            validated_data["body"],
        )
        event = Message.objects.compose(sender, recipient, body)
        if event is None:
            raise exceptions.PermissionDenied
        return event


class MessageEventSerializer(serializers.ModelSerializer[Event]):
    message = MessageSerializer()

    class Meta:
        model = Event
        fields = ("id", "type", "message", "date_created")


class ConversationSerializer(serializers.HyperlinkedModelSerializer[Conversation]):
    target = UserPublicReadSerializer(
        fields=(
            "id",
            "display_name",
            "username",
            "profile_picture",
            "is_private",
            "url",
        ),
        ref_name="ConversationUserTarget",
    )
    last_message = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField(
        method_name="get_messages_url",
        help_text="URL from which messages belonging to this chat can be retrieved.",
    )

    class Meta:
        model = Conversation
        fields = (
            "id",
            "target",
            "last_message",
            "date_created",
            "date_modified",
            "messages",
            "url",
        )
        extra_kwargs = {"url": {"view_name": "api:messaging:conversation-detail"}}

    @extend_schema_field(MessageSerializer(allow_null=True))
    def get_last_message(self, obj: Conversation) -> dict[str, Any] | None:
        if (msg := obj.last_message) is None:  # type: ignore[attr-defined]
            return None

        message = Message(**msg)
        serializer = MessageSerializer(message, context=self.context)
        return serializer.data

    @extend_schema_field(serializers.URLField)
    def get_messages_url(self, obj: Conversation) -> str:
        return reverse(
            "api:messaging:message-list",
            kwargs={"conversation_pk": obj.pk},
            request=self.context["request"],
        )


class ConversationDetailSerializer(ConversationSerializer):
    accept_required = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "target",
            "accept_required",
            "last_message",
            "date_created",
            "date_modified",
            "messages",
            "url",
        )
        extra_kwargs = {"url": {"view_name": "api:messaging:conversation-detail"}}

    def get_accept_required(self, conversation: Conversation) -> bool:
        return ConversationRequest.objects.filter(
            date_accepted__isnull=True,
            recipient=conversation.holder_id,
            sender=conversation.target_id,
        ).exists()


class ReadConversationSerializer(serializers.Serializer[dict[str, Any]]):
    until = serializers.DateTimeField()
    affected = serializers.IntegerField(read_only=True, min_value=0)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        conversation = self.context["conversation"]
        read_by = self.context["request"].user

        until = validated_data["until"]
        affected = conversation.messages.filter(
            recipient=read_by,
            date_read__isnull=True,
            date_created__lte=until,
        ).update(date_read=timezone.now())
        return {"until": until, "affected": affected}
