from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)

__all__ = ["email"]


email_create = extend_schema(
    summary="Send email verification",
    description="Used to change the e-mail of currently authenticated user."
    " Given that provided email that is not already taken,"
    " sends an e-mail containing a six-digit that could"
    " be used to verify the e-mail.",
    examples=[
        OpenApiExample(
            "e-mail taken",
            value={"email": ["This e-mail is already in use."]},
            response_only=True,
            status_codes=["400"],
        ),
        OpenApiExample(
            "e-mail is invalid",
            value={"email": ["Enter a valid email address."]},
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        201: RegistrationSerializer,
        400: OpenApiTypes.OBJECT,
    },
)

email_check = extend_schema(
    summary="Check email verification",
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
        OpenApiExample(
            "combination did not verify",
            value={"detail": "Not found."},
            response_only=True,
            status_codes=["404"],
        ),
        OpenApiExample(
            "fields have errors",
            value={
                "email": ["Enter a valid email address."],
                "code": [
                    "Ensure this field has at least 6 digits.",
                    "Ensure this field contains only digits.",
                ],
            },
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        200: RegistrationCheckSerializer,
        404: APIError,
        400: OpenApiTypes.OBJECT,
    },
)

email = {"create": email_create, "check": email_check}
