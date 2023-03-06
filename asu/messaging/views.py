from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

import django_filters

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.messaging.models import Conversation, ConversationRequest, Message
from asu.messaging.serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)
from asu.utils.rest import get_paginator
from asu.utils.views import ExtendedViewSet


class MessageViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "destroy")
    serializer_class = MessageSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    pagination_class = get_paginator("cursor", ordering="-date_created")

    def get_queryset(self):
        user, conversation_id = (
            self.request.user,
            self.kwargs["conversation_pk"],
        )
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user),
            conversations__id=conversation_id,
        )

    def perform_destroy(self, instance):
        conversation = instance.conversations.get(holder=self.request.user)
        conversation.messages.remove(instance)


class ConversationFilterSet(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(
        label="Type",
        method="filter_type",
        choices=[("requests", "Requests")],
    )

    def filter_type(self, queryset, name, value):
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

    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ConversationFilterSet

    def get_queryset(self):
        user = self.request.user
        queryset = Conversation.objects.filter(holder=user)

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
        serializer_class=serializers.Serializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def accept(self, request, pk):
        conversation = self.get_object()

        try:
            request = ConversationRequest.objects.get(
                sender=conversation.target,
                recipient=conversation.holder,
                date_accepted__isnull=True,
            )
        except ConversationRequest.DoesNotExist:
            return Response(status=204)  # Maintain idempotency

        request.date_accepted = timezone.now()
        request.save(update_fields=["date_accepted", "date_modified"])
        conversation.save(update_fields=["date_modified"])
        return Response(status=204)
