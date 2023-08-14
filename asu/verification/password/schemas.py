from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.utils import get_error_repr
from asu.utils.rest import APIError
from asu.verification.password.serializers import (
    PasswordResetVerificationCheckSerializer,
    PasswordResetVerificationSerializer,
)
from asu.verification.registration.schemas import consent_examples

__all__ = ["password_reset"]


password_reset_create = extend_schema(
    summary="Send password reset verification",
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
        201: PasswordResetVerificationSerializer,
        400: APIError,
    },
)

password_reset_check = extend_schema(
    summary="Check password reset verification",
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

password_reset = {"create": password_reset_create, "check": password_reset_check}
