from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property

from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, extend_schema

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.messaging import schemas
from asu.messaging.models import Conversation, ConversationRequest, Event, Interaction
from asu.messaging.serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    EventSerializer,
    ReadConversationSerializer,
)
from asu.utils.rest import EmptySerializer, get_paginator
from asu.utils.typing import UserRequest
from asu.utils.views import ExtendedViewSet


# todo add some sort of mechanism for replied message discovery
@extend_schema(parameters=[OpenApiParameter("conversation_id", int, "path")])
class EventViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    ExtendedViewSet[Event],
):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", page_size=25, ordering="-date_created")
    schemas = schemas.event

    @cached_property
    def conversation(self):
        # todo none of the mixins will work properly in
        # group context
        return get_object_or_404(
            Conversation.objects.only("id", "is_group"),
            holder=self.request.user,
            pk=self.kwargs["conversation_pk"],
        )

    def get_queryset(self) -> QuerySet[Event]:
        # Interactions should not include `read` types in the context of groups
        # since that could possibly result in loading a lot of objects. Also,
        # read interactions should only be visible to message sender. Senders
        # may display who viewed their messages via a separate API.
        interactions = Interaction.objects.all()
        if self.conversation.is_group:
            interactions = interactions.exclude(type="read")
        else:
            interactions = interactions.exclude(
                message__has_receipt=False,
                type="read",
            )
        return (
            Event.objects.select_related("message", "message__sender")
            .prefetch_related(
                Prefetch(
                    "message__interactions",
                    queryset=interactions,
                    to_attr="narrowed_interactions",
                )
            )
            .filter(conversation=self.conversation)
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
        # todo needs group refinement
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
        # todo only applicable to private
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
        # todo requires interaction, both group and private
        context = self.get_serializer_context()
        context["conversation"] = self.get_object()
        serializer = self.get_serializer(data=request.data, context=context)
        return self.get_action_save_response(request, serializer)
