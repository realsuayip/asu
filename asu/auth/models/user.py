from __future__ import annotations

import io
import uuid
from datetime import timedelta
from typing import Any, AnyStr

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core import signing
from django.core.files.base import ContentFile, File
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import oauthlib.common
import sorl.thumbnail
from oauth2_provider.models import AccessToken, RefreshToken
from oauth2_provider.settings import oauth2_settings
from PIL import Image
from sorl.thumbnail import get_thumbnail

from asu.auth.models import Application
from asu.auth.models.through import UserBlock, UserFollow, UserFollowRequest
from asu.messaging.models import ConversationRequest
from asu.utils.file import FileSizeValidator, MimeTypeValidator, UserContentPath


class UsernameValidator(RegexValidator):
    regex = r"^[a-zA-Z0-9]+(_[a-zA-Z0-9]+)*$"
    message = _(
        "Usernames can only contain latin letters,"
        " numerals and underscores. Trailing, leading or"
        " consecutive underscores are not allowed."
    )


class UserManager(DjangoUserManager["User"]):
    def public(self) -> QuerySet[User]:
        """
        Users who are publicly available.
        """
        return self.exclude(Q(is_active=False) | Q(is_frozen=True) | Q(is_private=True))

    def active(self) -> QuerySet[User]:
        """
        Users who are publicly available and can
        perform actions on the application.
        """
        return self.exclude(Q(is_active=False) | Q(is_frozen=True))

    def verify_ticket(
        self, ticket: str, *, ident: str, max_age: int
    ) -> tuple[int, str]:
        signer = signing.TimestampSigner()
        obj = signer.unsign_object(ticket, max_age=max_age)
        given_ident, value = obj.get("ident"), obj.get("value")
        if (not ident) or (not value) or ident != given_ident:
            raise signing.BadSignature
        pk, uuid = value
        return pk, uuid


class User(AbstractUser):  # type: ignore[django-manager-missing]
    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")
        OTHER = "other", _("Other")
        UNSPECIFIED = "unspecified", _("Unspecified")

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    # Personal information
    username = models.CharField(
        _("username"),
        max_length=16,
        validators=[MinLengthValidator(3), UsernameValidator()],
    )
    display_name = models.CharField(_("display name"), max_length=32)
    description = models.TextField(
        _("description"),
        blank=True,
        validators=[MaxLengthValidator(140)],
    )
    website = models.URLField(_("website"), blank=True)
    email = models.EmailField(_("e-mail"), unique=True)
    gender = models.CharField(
        _("gender"),
        max_length=12,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
    )
    birth_date = models.DateField(_("birth date"), null=True, blank=True)
    profile_picture = models.ImageField(
        _("profile picture"),
        blank=True,
        upload_to=UserContentPath("{instance.pk}/profile_picture/{uuid}{ext}"),
        validators=[
            FileSizeValidator(max_size=2**21),  # 2 MB
            MimeTypeValidator(allowed_types=["image/png", "image/jpeg"]),
        ],
    )

    # Messaging
    allows_receipts = models.BooleanField(
        _("allows message receipts"),
        default=True,
    )
    allows_all_messages = models.BooleanField(
        _("allows all incoming messages"),
        default=True,
        help_text=_(
            "Users that are not followed by this user can"
            " send message requests to them."
        ),
    )

    # Account flags
    is_frozen = models.BooleanField(
        _("frozen"),
        help_text=_("Designates whether this user has frozen their account."),
        default=False,
    )
    is_private = models.BooleanField(
        _("private"),
        help_text=_(
            "Users with private accounts has the privilege of hiding their identity."
        ),
        default=False,
    )

    # Relations with other users
    following = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="followed_by",
        through="account.UserFollow",
        blank=True,
    )
    blocked = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="blocked_by",
        through="account.UserBlock",
        blank=True,
    )

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()  # type: ignore[assignment]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="unique_lower_username",
                violation_error_message=_(
                    "The username you specified is already in use."
                ),
            ),
            models.CheckConstraint(
                check=Q(username__regex=UsernameValidator.regex),
                name="regex_valid_username",
                violation_error_message=UsernameValidator.message,
            ),
        ]

    def __str__(self) -> str:
        return self.username

    @property
    def is_accessible(self) -> bool:
        return self.is_active and (not self.is_frozen)

    def add_following(self, *, to_user: User) -> tuple[UserFollow, bool]:
        return UserFollow.objects.get_or_create(from_user=self, to_user=to_user)

    def send_follow_request(self, *, to_user: User) -> tuple[UserFollowRequest, bool]:
        return UserFollowRequest.objects.get_or_create(
            from_user=self,
            to_user=to_user,
            status=UserFollowRequest.Status.PENDING,
        )

    def get_pending_follow_requests(self) -> QuerySet[UserFollowRequest]:
        return UserFollowRequest.objects.filter(
            to_user=self, status=UserFollowRequest.Status.PENDING
        )

    def is_following(self, to_user: User) -> bool:
        return UserFollow.objects.filter(from_user=self, to_user=to_user).exists()

    def has_block_rel(self, to_user: User) -> bool:
        # Check symmetric blocking status
        return UserBlock.objects.filter(
            Q(from_user=self, to_user=to_user) | Q(from_user=to_user, to_user=self)
        ).exists()

    def can_send_message(self, to_user: User) -> bool:
        if self == to_user:
            return False

        if not (to_user.is_accessible and self.is_accessible):
            return False

        if self.has_block_rel(to_user):
            # One of the users is blocking
            # another, so deny messages.
            return False

        if to_user.is_following(self):
            # The sender is followed by recipient, so messaging should
            # happen without intervention. A message request will be created
            # and accepted automatically, so in the future, (when this
            # relation breaks) participants can continue messaging each
            # other without having to send/accept new conversation requests.
            return True

        # If the recipient is not following the sender, we need
        # to look into conversation request relations.

        # In case this sender previously sent a conversation
        # request, and it was accepted by the recipient.
        recipient_accepted_request = ConversationRequest.objects.filter(
            date_accepted__isnull=False,
            sender=self,
            recipient=to_user,
        )

        if recipient_accepted_request.exists():
            return True

        try:
            # Check if this message is sent as a reply. To reply,
            # the user needs to accept the request first, so 'accept
            # date' should not be null to send this message.
            replying = ConversationRequest.objects.get(
                sender=to_user,
                recipient=self,
            )
            return replying.date_accepted is not None
        except ConversationRequest.DoesNotExist:
            # Not a reply either, this means it might be a new
            # conversation request, or new messages are added to
            # unaccepted request. Let's check if the user allows message
            # requests from strangers.
            return to_user.allows_all_messages

    def create_ticket(self, *, ident: str) -> str:
        assert ident, "ident might not be empty"

        signer = signing.TimestampSigner()
        obj = {"ident": ident, "value": (self.pk, self.uuid.hex)}
        return signer.sign_object(obj)

    def set_profile_picture(self, file: File[AnyStr]) -> None:
        if self.profile_picture:
            sorl.thumbnail.delete(self.profile_picture, delete_file=False)
            self.profile_picture.delete(save=False)

        name = file.name
        thumb_io = io.BytesIO()
        image = Image.open(file)

        if image.mode != "RGB":
            image = image.convert("RGB")

        maxsize = 400
        width, height = image.size
        ratio = min(maxsize / width, maxsize / height)
        size = (int(width * ratio), int(height * ratio))

        image = image.resize(size, Image.LANCZOS)
        image.save(thumb_io, format="JPEG")

        self.profile_picture = ContentFile(thumb_io.getvalue(), name=name)
        self.save(update_fields=["profile_picture", "date_modified"])

    def get_profile_picture(self, size: tuple[int, int] = (72, 72)) -> str | None:
        if not self.profile_picture:
            return None

        geometry = "%sx%s" % size
        thumbnail: str | None = get_thumbnail(
            self.profile_picture,
            geometry,
            crop="center",
            quality=85,
        )
        return thumbnail

    def delete_profile_picture(self) -> None:
        image = self.profile_picture
        if image:
            sorl.thumbnail.delete(image, delete_file=False)
            image.delete(save=False)
            self.save(update_fields=["profile_picture", "date_modified"])

    def issue_token(self) -> dict[str, Any]:
        # Programmatically issue tokens for this user. Used just after
        # registration so that user can be logged in without having to
        # enter their password again.
        application = Application.objects.get_default()

        expires_seconds = oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
        expires = timezone.now() + timedelta(seconds=expires_seconds)
        scope = " ".join(oauth2_settings.SCOPES.keys())

        access = AccessToken.objects.create(
            user=self,
            scope=scope,
            expires=expires,
            token=oauthlib.common.generate_token(),
            application=application,
        )
        refresh = RefreshToken.objects.create(
            user=self,
            token=oauthlib.common.generate_token(),
            access_token=access,
            application=application,
        )
        return {
            "access_token": access.token,
            "token_type": "Bearer",
            "expires_in": expires_seconds,
            "refresh_token": refresh.token,
            "scope": scope,
        }
