from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, extend_schema

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.messaging import schemas
from asu.messaging.models import Conversation, ConversationRequest, Message
from asu.messaging.serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)
from asu.utils.rest import EmptySerializer, get_paginator
from asu.utils.views import ExtendedViewSet


@extend_schema(parameters=[OpenApiParameter("conversation_id", int, "path")])
class MessageViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "destroy")
    serializer_class = MessageSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", ordering="-date_created")
    schemas = schemas.message

    def get_queryset(self) -> QuerySet[Message]:
        if getattr(self, "swagger_fake_view", False):
            return Message.objects.none()

        user, conversation_id = (
            self.request.user,
            self.kwargs["conversation_pk"],
        )
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user),
            conversations__id=conversation_id,
        )

    def perform_destroy(self, instance: Message) -> None:
        conversation = instance.conversations.get(holder=self.request.user)
        conversation.messages.remove(instance)


class ConversationFilterSet(filters.FilterSet):
    type = filters.ChoiceFilter(
        label="Type",
        method="filter_type",
        choices=[("requests", "Requests")],
    )

    def filter_type(
        self, queryset: QuerySet[Conversation], name: str, value: str
    ) -> QuerySet[Conversation]:
        if value == "requests":
            return queryset.filter(
                Exists(
                    ConversationRequest.objects.filter(
                        date_accepted__isnull=True,
                        recipient=OuterRef("holder_id"),
                        sender=OuterRef("target_id"),
                    )
                )
            )
        return queryset  # pragma: no cover


class ConversationViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "destroy")
    serializer_class = ConversationSerializer
    serializer_classes = {"retrieve": ConversationDetailSerializer}
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", ordering="-date_modified")
    filter_backends = [filters.DjangoFilterBackend]
    schemas = schemas.conversation

    @property
    def filterset_class(self) -> type[filters.FilterSet] | None:
        if self.action == "list":
            return ConversationFilterSet
        return None

    def get_queryset(self) -> QuerySet[Conversation]:
        queryset = Conversation.objects.filter(holder=self.request.user)

        if self.action not in ("list", "retrieve"):
            # i.e., accept & destroy
            return queryset

        queryset = queryset.select_related("target")
        queryset = Conversation.objects.annotate_last_message(queryset)
        requests_only = self.request.GET.get("type") == "requests"

        if (self.action == "retrieve") or requests_only:
            return queryset

        # Regular "list" action
        request_accepted = Exists(
            ConversationRequest.objects.filter(
                date_accepted__isnull=False,
                recipient=OuterRef("holder_id"),
                sender=OuterRef("target_id"),
            )
        )
        request_sent = Exists(
            ConversationRequest.objects.filter(
                recipient=OuterRef("target_id"),
                sender=OuterRef("holder_id"),
            )
        )
        return queryset.filter(Q(request_sent) | Q(request_accepted))

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=EmptySerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def accept(self, request: Request, pk: int) -> Response:
        conversation = self.get_object()

        try:
            obj = ConversationRequest.objects.get(
                sender=conversation.target,
                recipient=conversation.holder,
                date_accepted__isnull=True,
            )
        except ConversationRequest.DoesNotExist:
            return Response(status=204)  # Maintain idempotency

        obj.date_accepted = timezone.now()
        obj.save(update_fields=["date_accepted", "date_modified"])
        conversation.save(update_fields=["date_modified"])
        return Response(status=204)
