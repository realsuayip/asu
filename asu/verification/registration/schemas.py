from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationVerificationCheckSerializer,
    RegistrationVerificationSendSerializer,
    UserCreateSerializer,
)

__all__ = ["registration"]


send = extend_schema(
    summary="Send registration verification",
    tags=[Tag.USER_REGISTRATION],
    description="Given that provided email that is not already taken,"
    " sends an e-mail containing a six-digit that could"
    " be used to verify the e-mail.",
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

consent_examples = [
    OpenApiExample(
        "success",
        value={
            "email": "test@example.com",
            "code": "595767",
            "consent": "21:1nG4Qe:VnTCqKDQvtLxLHLSt1lZ5nwGQF6gL8BQ6N_ywla_k9g",
        },
        response_only=True,
        status_codes=["200"],
    ),
    examples.not_found,
    OpenApiExample(
        "fields have errors",
        value=get_error_repr(
            {
                "email": ["Enter a valid email address."],
                "code": [
                    "Ensure this field has at least 6 digits.",
                    "Ensure this field contains only digits.",
                ],
            }
        ),
        response_only=True,
        status_codes=["400"],
    ),
]


verify = extend_schema(
    summary="Check registration verification",
    tags=[Tag.USER_REGISTRATION],
    description="Given an e-mail (one that received verification"
    " e-mail via related endpoint) and code, check if the pairs make"
    " a valid combination.",
    examples=consent_examples,
    responses={
        200: RegistrationVerificationCheckSerializer,
        404: APIError,
        400: APIError,
    },
)

complete = extend_schema(
    summary="Register a new user",
    tags=[Tag.USER_REGISTRATION],
    description="Before you send a request to this endpoint,"
    " you need to acquire 'consent' string. This string is obtained via "
    "email validation through registration verification flow. Check"
    " registration verification documentation to learn more.",
    examples=[
        OpenApiExample(
            "bad user information",
            value=get_error_repr(
                {
                    "email": ["Enter a valid email address."],
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
        OpenApiExample(
            "bad consent",
            value=get_error_repr(
                {
                    "email": [
                        "This e-mail could not be verified. Please provide a"
                        " validated e-mail address."
                    ]
                }
            ),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={201: UserCreateSerializer, 400: APIError},
)


registration = {
    "send": send,
    "verify": verify,
    "complete": complete,
}
