from django.db import models, transaction
from django.db.models import OuterRef, Q
from django.db.models.functions import JSONObject
from django.utils import timezone


class MessageManager(models.Manager):
    @transaction.atomic
    def compose(self, sender, recipient, body):
        if not sender.can_send_message(recipient):
            return None

        has_receipt = sender.allows_receipts and recipient.allows_receipts
        return self.create(
            sender=sender,
            recipient=recipient,
            body=body,
            has_receipt=has_receipt,
        )


class ConversationManager(models.Manager):
    def annotate_last_message(self, queryset):
        fields = (
            "id",
            "body",
            "sender_id",
            "has_receipt",
            "date_read",
            "date_created",
        )
        fields = dict(zip(fields, fields, strict=True))

        messages = (
            self.model.messages.rel.model.objects.filter(
                conversations=OuterRef("pk")
            )
            .order_by("-date_created")
            .values(data=JSONObject(**fields))
        )
        return queryset.annotate(last_message=messages[:1])


class ConversationRequestManager(models.Manager):
    def compose(self, sender, recipient):
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
