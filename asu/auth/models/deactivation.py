from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class UserDeactivation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
    )
    date_revoked = models.DateTimeField(
        _("date revoked"),
        null=True,
        blank=True,
    )

    date_created = models.DateTimeField(_("date created"), auto_now_add=True)
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)

    class Meta:
        verbose_name = _("account deactivation")
        verbose_name_plural = _("account deactivations")
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(date_revoked__isnull=True),
                name="unique_pending_user_deactivation",
            ),
        ]

    def __str__(self) -> str:
        return str(self.pk)
