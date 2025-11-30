from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationVerificationSendSerializer,
    UserCreateSerializer,
)

__all__ = ["registration"]


send = extend_schema(
    summary=_("Send registration verification"),
    tags=[Tag.USER_REGISTRATION],
    examples=[
        OpenApiExample(
            "e-mail is invalid",
            value=get_error_repr({"email": ["Enter a valid email address."]}),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        201: RegistrationVerificationSendSerializer,
        400: APIError,
    },
)

verify = extend_schema(
    summary=_("Verify registration verification"),
    tags=[Tag.USER_REGISTRATION],
    examples=[
        examples.not_found,
        OpenApiExample(
            "fields have errors",
            value=get_error_repr({"code": ["Please enter a valid code."]}),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        204: None,
        400: APIError,
        404: APIError,
    },
)

complete = extend_schema(
    summary=_("Register a new user"),
    tags=[Tag.USER_REGISTRATION],
    examples=[
        examples.not_found,
        OpenApiExample(
            "bad user information",
            value=get_error_repr(
                {
                    "display_name": ["This field may not be blank."],
                    "username": [
                        "Usernames can only contain latin letters,"
                        "numerals and underscores. Trailing, leading"
                        " or consecutive underscores are not allowed."
                    ],
                }
            ),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        201: UserCreateSerializer,
        400: APIError,
        404: APIError,
    },
)


registration = {
    "send": send,
    "verify": verify,
    "complete": complete,
}
