from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models import OuterRef, Q, QuerySet
from django.db.models.functions import JSONObject
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from asu.auth.models import User


class ConversationManager(models.Manager["Conversation"]):
    def annotate_last_message(
        self, queryset: QuerySet[Conversation]
    ) -> QuerySet[Conversation]:
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
            self.model.messages.rel.model.objects.filter(conversations=OuterRef("pk"))
            .order_by("-date_created")
            .values(data=JSONObject(**mapping))
        )
        return queryset.annotate(last_message=messages[:1])


class Conversation(models.Model):
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name=_("holder"),
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="targeted_conversations",
        verbose_name=_("target"),
    )

    messages = models.ManyToManyField(
        "Message", related_name="conversations", verbose_name=_("messages")
    )

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ConversationManager()

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        constraints = [
            models.UniqueConstraint(
                fields=["holder", "target"],
                name="unique_conversation",
            )
        ]


class ConversationRequestManager(models.Manager["ConversationRequest"]):
    def compose(
        self, sender: User, recipient: User
    ) -> tuple[ConversationRequest, bool]:
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


class ConversationRequest(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("sender"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("recipient"),
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
