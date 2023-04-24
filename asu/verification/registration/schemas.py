from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)

__all__ = ["registration"]


registration_create = extend_schema(
    summary="Send registration verification",
    description="Given that provided email that is not already taken,"
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
]


registration_check = extend_schema(
    summary="Check registration verification",
    description="Given an e-mail (one that received verification"
    " e-mail via related endpoint) and code, check if the pairs make"
    " a valid combination.",
    examples=consent_examples,
    responses={
        200: RegistrationCheckSerializer,
        404: APIError,
        400: OpenApiTypes.OBJECT,
    },
)

registration = {"create": registration_create, "check": registration_check}
