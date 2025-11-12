"""
Includes messages that are either:

a) Too long to include in actual code,
such as email messages, to preserve readability.

b) Reused throughout the application, such as
generic error messages.
"""

import typing

from django.utils.translation import gettext_lazy as _

if typing.TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise


class EmailMessage(typing.NamedTuple):
    subject: StrOrPromise
    body: StrOrPromise


GENERIC_ERROR = _("We could not handle your request. Please try again later.")
BAD_VERIFICATION_CODE = _(
    "We couldn't verify your code. Please make sure you've"
    " entered the correct code that was sent to your email. If the"
    " problem persists, please request a new verification code or"
    " contact support for assistance."
)


# Email messages

password_reset = EmailMessage(
    subject=_("Verify your email to reset your password"),
    body=_(
        "To continue for the password reset process,"
        " you need to enter the following code into"
        " the application:"
    ),
)
password_change_notice = EmailMessage(
    subject=_("Your password has been changed"),
    body=_(
        "The password for your account was just changed. If this was you,"
        " you can safely ignore this email. Otherwise, reset your password"
        " immediately, or contact the support team to restore your password."
    ),
)
registration = EmailMessage(
    subject=_("Verify your email for registration"),
    body=_(
        "To continue for the registration process,"
        " you need to enter the following code into"
        " the application:"
    ),
)
email_verification = EmailMessage(
    subject=_("Verify this email address"),
    body=_(
        "To change your email, you need to enter the following"
        " code into the application:"
    ),
)
account_deactivated = EmailMessage(
    subject=_("Your account has been deactivated"),
    body=_(
        "You have now deactivated your account. Your account will be"
        " permanently deleted in 30 days. If you change your mind,"
        " you can simply login to reactivate your account."
    ),
)
