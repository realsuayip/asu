from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from rest_framework import permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

import django_filters

from zeynep.messaging.models import Conversation, ConversationRequest, Message
from zeynep.messaging.serializers import (
    ConversationSerializer,
    MessageSerializer,
)
from zeynep.utils.rest import get_paginator
from zeynep.utils.views import ExtendedViewSet


class MessageViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "destroy")
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = get_paginator("cursor", ordering="-date_created")

    def get_queryset(self):
        return Message.objects.filter(
            conversations__id=self.kwargs["conversation_pk"]
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
            return Conversation.objects.filter(
                Exists(
                    ConversationRequest.objects.filter(
                        date_accepted__isnull=True,
                        recipient=OuterRef("holder_id"),
                    )
                ),
                holder=self.request.user,
            ).select_related("target")
        return queryset  # pragma: no cover


class ConversationViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "destroy")
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = get_paginator("cursor", ordering="-date_modified")

    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ConversationFilterSet

    def get_queryset(self):
        user = self.request.user

        if self.action == "list":
            request_accepted = Exists(
                ConversationRequest.objects.filter(
                    date_accepted__isnull=False,
                    recipient=OuterRef("holder_id"),
                )
            )
            request_sent = Exists(
                ConversationRequest.objects.filter(
                    recipient=OuterRef("target_id")
                )
            )
            return Conversation.objects.filter(
                Q(request_sent) | Q(request_accepted),
                holder=user,
            )

        return Conversation.objects.filter(holder=user)

    @action(
        detail=True,
        methods=["post"],
        serializer_class=serializers.Serializer,
    )
    def accept(self, request, pk):
        conversation = self.get_object()

        try:
            request = ConversationRequest.objects.get(
                recipient=conversation.holder,
                date_accepted__isnull=True,
            )
        except ConversationRequest.DoesNotExist:
            return Response(status=204)  # Maintain idempotency

        request.date_accepted = timezone.now()
        request.save(update_fields=["date_accepted", "date_modified"])
        conversation.save(update_fields=["date_modified"])
        return Response(status=204)
