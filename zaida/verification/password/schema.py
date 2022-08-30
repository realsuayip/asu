from drf_spectacular.utils import OpenApiExample, OpenApiTypes, extend_schema

from zaida.verification.password.serializers import (
    PasswordResetVerificationCheckSerializer,
    PasswordResetVerificationSerializer,
)
from zaida.verification.registration.schema import consent_examples

password_reset_create = extend_schema(
    summary="Password Reset: send email verification",
    description="The provided email will receive a code to verify the"
    " user. The consent for password resetting process is"
    " obtained with this code and email pair.",
    examples=[
        OpenApiExample(
            "e-mail is invalid",
            value={"email": ["Enter a valid email address."]},
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={
        201: PasswordResetVerificationSerializer,
        400: OpenApiTypes.OBJECT,
    },
)

password_reset_check = extend_schema(
    summary="Password Reset: check email verification",
    description="Given an e-mail (one that received verification"
    " e-mail via related endpoint) and code, check if the pairs make"
    " a valid combination. The returned consent is required to actually"
    " reset the password.",
    examples=consent_examples,
    responses={
        200: PasswordResetVerificationCheckSerializer,
        404: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
    },
)
