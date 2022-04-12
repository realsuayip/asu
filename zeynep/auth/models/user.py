from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

from zeynep.auth.models.managers import UserManager


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
