from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.registration.serializers import (
    RegistrationVerificationSendSerializer,
)

__all__ = ["email"]


send = extend_schema(
    summary=_("Send email verification"),
    tags=[Tag.USER_EMAIL_CHANGE],
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
    summary=_("Verify email verification"),
    tags=[Tag.USER_EMAIL_CHANGE],
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

email = {"send": send, "complete": complete}
