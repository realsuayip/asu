import types

from drf_spectacular.utils import extend_schema

from asu.messaging.serializers import ConversationDetailSerializer
from asu.utils.rest import APIError

message = types.SimpleNamespace(
    list=extend_schema(summary="List messages"),
    retrieve=extend_schema(summary="Retrieve a message"),
    destroy=extend_schema(
        summary="Delete a message", responses={204: None, 404: APIError}
    ),
)


conversation = types.SimpleNamespace(
    list=extend_schema(summary="List conversations"),
    retrieve=extend_schema(
        summary="Retrieve a conversation",
        responses={200: ConversationDetailSerializer, 404: APIError},
    ),
    destroy=extend_schema(
        summary="Delete a conversation", responses={204: None, 404: APIError}
    ),
    accept=extend_schema(
        summary="Accept message request", responses={204: None, 404: APIError}
    ),
)
