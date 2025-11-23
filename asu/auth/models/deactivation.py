from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from asu.core.models.base import Base


class UserDeactivation(Base):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deactivations",
        verbose_name=_("user"),
    )
    revoked = models.DateTimeField(_("date revoked"), null=True, blank=True)
    for_deletion = models.BooleanField(
        _("for deletion"),
        help_text=_("Marks this user for permanent deletion."),
        default=False,
    )

    class Meta:
        verbose_name = _("user deactivation")
        verbose_name_plural = _("user deactivations")
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(revoked__isnull=True),
                name="unique_pending_user_deactivation",
            ),
        ]

    def __str__(self) -> str:
        return str(self.pk)
