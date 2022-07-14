from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from zeynep.messaging.models.managers import MessageManager


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
