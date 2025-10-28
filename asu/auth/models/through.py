from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class UserThrough(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="from_%(class)ss",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="to_%(class)ss",
    )
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_%(app_label)s_%(class)s",
            )
        ]
        abstract = True

    def __str__(self) -> str:
        return "from=%s, to=%s" % (self.from_user_id, self.to_user_id)


class UserFollow(UserThrough):
    pass


class UserBlock(UserThrough):
    pass


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
        indexes = [
            models.Index(
                fields=["status", "from_user", "to_user"],
                name="follow_request_frequents",
            ),
        ]

    @property
    def is_pending(self) -> bool:
        return self.status == UserFollowRequest.Status.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    def is_rejected(self) -> bool:
        return self.status == self.Status.REJECTED

    @transaction.atomic
    def accept(self) -> None:
        assert self.is_pending
        self.status = self.Status.APPROVED
        self.save(update_fields=["status", "date_modified"])
        self.from_user.add_following(to_user=self.to_user)

    def reject(self) -> None:
        assert self.is_pending
        self.status = self.Status.REJECTED
        self.save(update_fields=["status", "date_modified"])
