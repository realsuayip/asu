from django.contrib.auth.models import AbstractUser
from django.core import signing
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from zeynep.auth.models.managers import UserManager
from zeynep.auth.models.through import UserBlock, UserFollow, UserFollowRequest
from zeynep.messaging.models import ConversationRequest


class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")
        OTHER = "other", _("Other")
        UNSPECIFIED = "unspecified", _("Unspecified")

    # Personal information
    username = models.CharField(
        _("username"),
        max_length=16,
        unique=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                regex=r"^[a-z0-9]+(_[a-z0-9]+)*$",
                message=_(
                    "Usernames can only contain latin letters,"
                    " numerals and underscores. Trailing, leading or"
                    " consecutive underscores are not allowed."
                ),
            ),
        ],
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
            "Users with private accounts has the"
            " privilege of hiding their identity."
        ),
        default=False,
    )

    # Relations with other users
    following = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="followed_by",
        through="zeynep_auth.UserFollow",
        blank=True,
    )
    blocked = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="blocked_by",
        through="zeynep_auth.UserBlock",
        blank=True,
    )

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.username

    @property
    def is_accessible(self):
        return self.is_active and (not self.is_frozen)

    def add_following(self, *, to_user):
        return UserFollow.objects.get_or_create(
            from_user=self, to_user=to_user
        )

    def send_follow_request(self, *, to_user):
        return UserFollowRequest.objects.get_or_create(
            from_user=self,
            to_user=to_user,
            status=UserFollowRequest.Status.PENDING,
        )

    def get_pending_follow_requests(self):
        return UserFollowRequest.objects.filter(
            to_user=self, status=UserFollowRequest.Status.PENDING
        )

    def is_following(self, to_user):
        return UserFollow.objects.filter(
            from_user=self, to_user=to_user
        ).exists()

    def has_block_rel(self, to_user):
        # Check symmetric blocking status
        return UserBlock.objects.filter(
            Q(from_user=self, to_user=to_user)
            | Q(from_user=to_user, to_user=self)
        ).exists()

    def can_send_message(self, to_user):
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

    def create_ticket(self, scope):
        if scope == "websocket":
            signer = signing.TimestampSigner(salt=scope)
            return signer.sign(self.pk)
        return None
