from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationVerificationCheckSerializer,
    RegistrationVerificationSendSerializer,
)

__all__ = ["email"]


send = extend_schema(
    summary="Send email verification",
    tags=[Tag.USER_EMAIL_CHANGE],
    description="Used to change the e-mail of currently authenticated user."
    " Given that provided email that is not already taken,"
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

complete = extend_schema(
    summary="Check email verification",
    tags=[Tag.USER_EMAIL_CHANGE],
    description="Given an e-mail (one that received verification"
    " e-mail via related endpoint) and code, check if the pairs make"
    " a valid combination. <strong>If they do, e-mail of the currently"
    " authenticated user will be changed.</strong>",
    examples=[
        OpenApiExample(
            "success",
            value={"email": "test@example.com", "code": "595767"},
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
    ],
    responses={
        200: RegistrationVerificationCheckSerializer,
        404: APIError,
        400: APIError,
    },
)

email = {"send": send, "complete": complete}
