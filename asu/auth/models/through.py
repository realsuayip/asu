from django.conf import settings
from django.db import models
from django.db.models import Q
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


class UserFollowRequest(UserThrough):
    class Status(models.TextChoices):
        PENDING = "pending", _("pending")
        APPROVED = "approved", _("approved")
        REJECTED = "rejected", _("rejected")

    status = models.CharField(
        _("status"),
        max_length=8,
        choices=Status.choices,
        default=Status.PENDING,
    )
    date_modified = models.DateTimeField(_("date modified"), auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                condition=Q(status="pending"),
                name="unique_user_follow_request",
            )
        ]

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    def bond(self) -> None:
        # Create the actual following relationship.
        assert self.is_approved, "Attempt to bond unapproved instance"
        self.from_user.add_following(to_user=self.to_user)
