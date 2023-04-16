from typing import TYPE_CHECKING, Union

from django.db import models, transaction
from django.db.models import OuterRef, Q, QuerySet
from django.db.models.functions import JSONObject
from django.utils import timezone

if TYPE_CHECKING:
    from asu.auth.models import User
    from asu.messaging.models import Conversation, ConversationRequest, Message


class MessageManager(models.Manager["Message"]):
    @transaction.atomic
    def compose(
        self, sender: "User", recipient: "User", body: str
    ) -> Union["Message", None]:
        if not sender.can_send_message(recipient):
            return None

        has_receipt = sender.allows_receipts and recipient.allows_receipts
        return self.create(
            sender=sender,
            recipient=recipient,
            body=body,
            has_receipt=has_receipt,
        )


class ConversationManager(models.Manager["Conversation"]):
    def annotate_last_message(
        self, queryset: QuerySet["Conversation"]
    ) -> QuerySet["Conversation"]:
        fields = (
            "id",
            "body",
            "sender_id",
            "has_receipt",
            "date_read",
            "date_created",
        )
        mapping = dict(zip(fields, fields, strict=True))

        messages = (
            self.model.messages.rel.model.objects.filter(
                conversations=OuterRef("pk")
            )
            .order_by("-date_created")
            .values(data=JSONObject(**mapping))
        )
        return queryset.annotate(last_message=messages[:1])


class ConversationRequestManager(models.Manager["ConversationRequest"]):
    def compose(
        self, sender: "User", recipient: "User"
    ) -> tuple["ConversationRequest", bool]:
        try:
            obj = self.get(
                Q(sender=sender, recipient=recipient)
                | Q(sender=recipient, recipient=sender)
            )
        except self.model.DoesNotExist:
            obj = None

        is_following = recipient.is_following(sender)

        if obj is not None:
            # A follow relation has been formed since the request
            # first created; automatically accept the request.
            if is_following and (obj.date_accepted is None):
                obj.date_accepted = timezone.now()
                obj.save(update_fields=["date_accepted", "date_modified"])
            return obj, False

        kwargs = {"sender": sender, "recipient": recipient}
        defaults = None

        if is_following:
            defaults = {"date_accepted": timezone.now()}
        return self.get_or_create(**kwargs, defaults=defaults)
