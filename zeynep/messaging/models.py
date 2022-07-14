from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


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

        if is_following:
            kwargs["date_accepted"] = timezone.now()

        obj = self.create(**kwargs)
        return obj, True


class Message(models.Model):
    body = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    has_receipt = models.BooleanField(default=True)

    date_read = models.DateTimeField(_("date read"), null=True, blank=True)
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = MessageManager()

    @cached_property
    def sender_conversation(self):
        # Used in "MessageComposeSerializer" to retrieve related
        # conversation hyperlink.
        return self.conversations.only("pk").get(holder=self.sender)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self):
        return "%s <%s>" % (self._meta.verbose_name.title(), self.pk)


class Conversation(models.Model):
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="targeted_conversations",
    )

    messages = models.ManyToManyField("Message", related_name="conversations")

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["holder", "target"],
                name="unique_conversation",
            )
        ]

    def __str__(self):
        return "%s <%s>" % (self._meta.verbose_name.title(), self.pk)


class ConversationRequest(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    date_accepted = models.DateTimeField(
        _("date_accepted"),
        null=True,
        blank=True,
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ConversationRequestManager()

    class Meta:
        verbose_name = _("conversation request")
        verbose_name_plural = _("conversation requests")
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "recipient"],
                name="unique_conversation_request",
            )
        ]
