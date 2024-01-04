from drf_spectacular.utils import extend_schema

from asu.messaging.serializers import (
    ConversationDetailSerializer,
    ReadConversationSerializer,
)
from asu.utils.openapi import examples
from asu.utils.rest import APIError

__all__ = ["message", "conversation"]

message = {
    "list": extend_schema(summary="List messages"),
    "retrieve": extend_schema(summary="Retrieve a message"),
    "destroy": extend_schema(
        summary="Delete a message",
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
}


conversation = {
    "list": extend_schema(summary="List conversations"),
    "retrieve": extend_schema(
        summary="Retrieve a conversation",
        responses={200: ConversationDetailSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "destroy": extend_schema(
        summary="Delete a conversation",
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
    "accept": extend_schema(
        summary="Accept message request",
        responses={204: None, 404: APIError},
        examples=[examples.not_found],
    ),
    "read": extend_schema(
        summary="Read a conversation",
        description="Reading a conversation will mark"
        " received messages as read, until the specified threshold.",
        responses={200: ReadConversationSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
}
