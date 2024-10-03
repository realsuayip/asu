from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import Case, OuterRef, Q, QuerySet, When
from django.db.models.functions import JSONObject
from django.utils.translation import gettext_lazy as _


class ConversationManager(models.Manager["Conversation"]):
    def annotate_last_message(
        self, queryset: QuerySet[Conversation]
    ) -> QuerySet[Conversation]:
        fields = (
            "id",
            "body",
            "sender_id",
            "has_receipt",
            "reply_to_id",
            "date_created",
        )
        mapping = dict(zip(fields, fields, strict=True))

        # todo requires optimization and possibly different serializer.
        # maybe we'll just append last event instead?
        messages = (
            apps.get_model("messaging.Message")
            .objects.filter(events__conversation=OuterRef("pk"))
            .order_by("-events__date_created")
            .values(data=JSONObject(**mapping))
        )
        return queryset.annotate(last_message=messages[:1])


class Conversation(models.Model):
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="conversations",
        verbose_name=_("holder"),
        help_text=_(
            "In private conversations, this field holds one of the participants."
            " In group conversations, this field holds the creator of the conversation."
        ),
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="targeted_conversations",
        verbose_name=_("target"),
    )
    is_group = models.BooleanField(_("group"), default=False)

    # Group-exclusive fields
    name = models.CharField(_("name"), max_length=100, blank=True)
    description = models.TextField(_("description"), blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("participants"),
        through="messaging.Participation",
        blank=True,
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
                condition=Q(is_group=False),
                name="unique_private_conversation",
            ),
            # todo separate these
            models.CheckConstraint(
                check=Case(
                    When(
                        is_group=False,
                        then=Q(holder__isnull=False) & Q(target__isnull=False),
                    ),
                    When(
                        is_group=True,
                        then=Q(holder__isnull=False) & Q(target__isnull=True),
                    ),
                    default=False,
                    output_field=models.BooleanField(),
                ),
                name="valid_private_conversation",
                violation_error_message=_(
                    "Private conversations must have valid holder and target fields."
                ),
            ),
            #         "Group conversations must have a valid name and holder,"
            #         " and the target must be null."
        ]
        indexes = [
            models.Index(fields=["date_modified"]),
        ]

    def __str__(self) -> str:
        return str(self.pk)
