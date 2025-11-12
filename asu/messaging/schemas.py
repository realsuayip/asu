from drf_spectacular.utils import extend_schema

from asu.core.utils.openapi import Tag, examples
from asu.core.utils.rest import APIError
from asu.messaging.serializers import (
    ConversationDetailSerializer,
    MessageSerializer,
    ReadConversationSerializer,
)

__all__ = [
    "conversation",
    "message",
]

message = {
    "list": extend_schema(
        summary="List messages",
        tags=[Tag.MESSAGING],
        responses={200: MessageSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "retrieve": extend_schema(
        summary="Retrieve a message",
        tags=[Tag.MESSAGING],
        responses={200: MessageSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "destroy": extend_schema(
        summary="Delete a message",
        tags=[Tag.MESSAGING],
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
}


conversation = {
    "list": extend_schema(summary="List conversations", tags=[Tag.MESSAGING]),
    "retrieve": extend_schema(
        summary="Retrieve a conversation",
        tags=[Tag.MESSAGING],
        responses={200: ConversationDetailSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "destroy": extend_schema(
        summary="Delete a conversation",
        tags=[Tag.MESSAGING],
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
    "accept": extend_schema(
        summary="Accept message request",
        tags=[Tag.MESSAGING],
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
    "read": extend_schema(
        summary="Read a conversation",
        tags=[Tag.MESSAGING],
        description="Reading a conversation will mark"
        " received messages as read, until the specified threshold.",
        responses={200: ReadConversationSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
}
