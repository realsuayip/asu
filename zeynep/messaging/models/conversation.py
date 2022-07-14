from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from zeynep.messaging.models.managers import ConversationRequestManager


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
