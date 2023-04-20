import datetime
from typing import Any

from rest_framework import exceptions, serializers
from rest_framework.reverse import reverse

from django_stubs_ext import WithAnnotations
from drf_spectacular.utils import extend_schema_field

from asu.auth.serializers.user import UserPublicReadSerializer
from asu.messaging.models import Conversation, ConversationRequest, Message


class MessageComposeSerializer(serializers.ModelSerializer[Message]):
    conversation = serializers.HyperlinkedRelatedField(  # type: ignore[var-annotated]
        read_only=True,
        view_name="api:conversation-detail",
        source="sender_conversation",
    )
    url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "body",
            "conversation",
            "date_created",
            "url",
        )

    def get_url(self, obj: Message) -> str:
        return reverse(
            "api:message-detail",
            kwargs={
                "pk": obj.pk,
                "conversation_pk": obj.sender_conversation.pk,
            },
            request=self.context["request"],
        )

    def create(self, validated_data: dict[str, Any]) -> Message:
        sender = self.context["request"].user
        recipient = self.context["recipient"]
        body = validated_data["body"]

        message = Message.objects.compose(sender, recipient, body)

        if message is None:
            raise exceptions.PermissionDenied

        return message


class MessageSerializer(serializers.ModelSerializer[Message]):
    date_read = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()  # type: ignore[assignment]

    class Meta:
        model = Message
        fields = ("id", "body", "source", "date_created", "date_read")

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_date_read(self, message: Message) -> datetime.datetime | None:
        return message.date_read if message.has_receipt else None

    @extend_schema_field(serializers.ChoiceField(choices=["sent", "received"]))
    def get_source(self, message: Message) -> str:
        user = self.context["request"].user
        return "sent" if message.sender_id == user.pk else "received"


class ConversationSerializer(serializers.HyperlinkedModelSerializer):
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
        extra_kwargs = {"url": {"view_name": "api:conversation-detail"}}

    @extend_schema_field(MessageSerializer(allow_null=True))
    def get_last_message(
        self, obj: WithAnnotations[Conversation]
    ) -> dict[str, Any] | None:
        if obj.last_message is None:
            return None

        message = Message(**obj.last_message)
        serializer = MessageSerializer(message, context=self.context)
        return serializer.data

    @extend_schema_field(serializers.URLField)
    def get_messages_url(self, obj: Conversation) -> str:
        return reverse(
            "api:message-list",
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
        extra_kwargs = {"url": {"view_name": "api:conversation-detail"}}

    def get_accept_required(self, conversation: Conversation) -> bool:
        return ConversationRequest.objects.filter(
            date_accepted__isnull=True,
            recipient=conversation.holder_id,
            sender=conversation.target_id,
        ).exists()
