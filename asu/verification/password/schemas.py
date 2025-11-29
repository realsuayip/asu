from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.core.utils.openapi import Tag, get_error_repr
from asu.core.utils.rest import APIError
from asu.verification.password.serializers import (
    PasswordResetSerializer,
    PasswordResetVerificationCheckSerializer,
    PasswordResetVerificationSendSerializer,
)
from asu.verification.registration.schemas import consent_examples

__all__ = ["password_reset"]


send = extend_schema(
    summary="Send password reset verification",
    tags=[Tag.USER_PASSWORD_RESET],
    description="The provided email will receive a code to verify the"
    " user. The consent for password resetting process is"
    " obtained with this code and email pair.",
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
    summary="Check password reset verification",
    tags=[Tag.USER_PASSWORD_RESET],
    description="Given an e-mail (one that received verification"
    " e-mail via related endpoint) and code, check if the pairs make"
    " a valid combination. The returned consent is required to actually"
    " reset the password.",
    examples=consent_examples,
    responses={
        200: PasswordResetVerificationCheckSerializer,
        404: APIError,
        400: APIError,
    },
)
complete = extend_schema(
    summary="Reset password",
    tags=[Tag.USER_PASSWORD_RESET],
    responses={
        200: PasswordResetSerializer,
        400: APIError,
    },
    examples=[
        OpenApiExample(
            "bad values",
            value=get_error_repr(
                {
                    "email": ["This e-mail could not be verified."],
                    "password": [
                        "This password is too common.",
                        "This password is too short. It must contain at"
                        " least 8 characters.",
                    ],
                }
            ),
            response_only=True,
            status_codes=["400"],
        )
    ],
)

password_reset = {
    "send": send,
    "verify": verify,
    "complete": complete,
}
