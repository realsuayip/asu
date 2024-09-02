from django.db.models import Exists, OuterRef, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, extend_schema

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.messaging import schemas
from asu.messaging.models import Conversation, ConversationRequest, Event, Message
from asu.messaging.serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageEventSerializer,
    ReadConversationSerializer,
)
from asu.utils.rest import EmptySerializer, get_paginator
from asu.utils.typing import UserRequest
from asu.utils.views import ExtendedViewSet


@extend_schema(parameters=[OpenApiParameter("conversation_id", int, "path")])
class MessageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    ExtendedViewSet[Message],
):
    queryset = Event.objects.none()
    serializer_class = MessageEventSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", ordering="-date_created")
    schemas = schemas.message

    def get_queryset(self) -> QuerySet[Message]:
        self.conversation = get_object_or_404(
            Conversation.objects.only("id"),
            holder=self.request.user,
            pk=self.kwargs["conversation_pk"],
        )
        return Event.objects.select_related("message", "message__sender").filter(
            type="message", conversation=self.conversation
        )


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


class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    ExtendedViewSet[Conversation],
):
    queryset = Conversation.objects.none()
    serializer_class = ConversationSerializer
    serializer_classes = {"retrieve": ConversationDetailSerializer}
    filterset_classes = {"list": ConversationFilterSet}
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", ordering="-date_modified")
    filter_backends = [filters.DjangoFilterBackend]
    schemas = schemas.conversation

    def get_queryset(self) -> QuerySet[Conversation]:
        holder = self.request.user
        queryset = Conversation.objects.filter(holder=holder)

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
                recipient=holder.id,
                sender=OuterRef("target_id"),
            )
        )
        request_sent = Exists(
            ConversationRequest.objects.filter(
                recipient=OuterRef("target_id"),
                sender=holder.id,
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

    @action(
        detail=True,
        methods=["patch"],
        serializer_class=ReadConversationSerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def read(self, request: UserRequest, pk: int) -> Response:
        context = self.get_serializer_context()
        context["conversation"] = self.get_object()
        serializer = self.get_serializer(data=request.data, context=context)
        return self.get_action_save_response(request, serializer)
