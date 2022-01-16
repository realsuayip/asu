from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserThrough(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        abstract = True


class UserFollow(UserThrough):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"], name="unique_user_follow"
            )
        ]


class UserBlock(UserThrough):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"], name="unique_user_block"
            )
        ]
