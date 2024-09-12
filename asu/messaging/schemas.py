from drf_spectacular.utils import extend_schema

from asu.messaging.serializers import (
    ConversationDetailSerializer,
    EventSerializer,
    ReadConversationSerializer,
)
from asu.utils.openapi import examples
from asu.utils.rest import APIError

__all__ = ["event", "conversation"]


event = {
    "list": extend_schema(
        summary="List conversation events",
        responses={200: EventSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "retrieve": extend_schema(
        summary="Retrieve a conversation event",
        responses={200: EventSerializer, 404: APIError},
        examples=[examples.not_found],
    ),
    "destroy": extend_schema(
        summary="Delete a conversation event",
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
