"""
Includes messages that are either:

a) Too long to include in actual code,
such as email messages, to preserve readability.

b) Reused throughout the application, such as
generic error messages.
"""

from collections import namedtuple

from django.utils.translation import gettext_lazy as _

EmailMessage = namedtuple("EmailMessage", ["subject", "body"])


GENERIC_ERROR = _("We could not handle your request. Please try again later.")


# Email messages

password_reset = EmailMessage(
    subject=_("Verify your email to reset your password"),
    body=_(
        "To continue for the password reset process,"
        " you need to enter the following code into"
        " the application:"
        "<div class='code'><strong>%(code)s</strong></div>"
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
        "<div class='code'><strong>%(code)s</strong></div>"
    ),
)
email_verification = EmailMessage(
    subject=_("Verify this email address"),
    body=_(
        "To change your email, you need to enter the following"
        " code into the application:"
        "<div class='code'><strong>%(code)s</strong></div>"
    ),
)
