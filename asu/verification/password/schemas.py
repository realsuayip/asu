from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.password.serializers import (
    PasswordResetSerializer,
    PasswordResetVerificationSendSerializer,
)

__all__ = ["password_reset"]


send = extend_schema(
    summary=_("Send password reset verification"),
    tags=[Tag.USER_PASSWORD_RESET],
    examples=[
        OpenApiExample(
            "e-mail is invalid",
            value=get_error_repr({"email": ["Enter a valid email address."]}),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        201: PasswordResetVerificationSendSerializer,
        400: APIError,
    },
)

verify = extend_schema(
    summary=_("Verify password reset verification"),
    tags=[Tag.USER_PASSWORD_RESET],
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
    summary="Reset password",
    tags=[Tag.USER_PASSWORD_RESET],
    responses={
        200: PasswordResetSerializer,
        400: APIError,
        404: APIError,
    },
    examples=[
        examples.not_found,
        OpenApiExample(
            "bad values",
            value=get_error_repr(
                {
                    "password": [
                        "This password is too common.",
                        "This password is too short. It must contain at"
                        " least 8 characters.",
                    ],
                }
            ),
            response_only=True,
            status_codes=["400"],
        ),
    ],
)

password_reset = {
    "send": send,
    "verify": verify,
    "complete": complete,
}
