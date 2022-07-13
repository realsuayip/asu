from rest_framework import exceptions, serializers

from zeynep.auth.serializers.user import UserPublicReadSerializer
from zeynep.messaging.models import Conversation, Message


class MessageComposeSerializer(serializers.HyperlinkedModelSerializer):
    conversation = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name="conversation-detail",
        source="sender_conversation",
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "body",
            "conversation",
            "conversation",
            "date_created",
        )

    def create(self, validated_data):
        sender = self.context["request"].user
        recipient = self.context["recipient"]
        body = validated_data["body"]

        message = Message.objects.compose(sender, recipient, body)

        if message is None:
            raise exceptions.PermissionDenied

        return message


class MessageSerializer(serializers.ModelSerializer):
    date_read = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "body", "date_created", "date_read")

    def get_date_read(  # noqa
        self, message
    ) -> serializers.DateTimeField(allow_null=True):
        return message.date_read if message.has_receipt else None


class ConversationSerializer(serializers.HyperlinkedModelSerializer):
    target = UserPublicReadSerializer(
        fields=(
            "id",
            "display_name",
            "username",
            "is_private",
            "url",
        )
    )

    class Meta:
        model = Conversation
        fields = (
            "id",
            "target",
            "date_created",
            "date_modified",
            "url",
        )
