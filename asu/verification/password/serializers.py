import functools
from typing import Any, NoReturn

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers

from asu.auth.models import User
from asu.core.utils import messages
from asu.verification.models import PasswordResetVerification
from asu.verification.serializers import BaseCheckSerializer
from asu.verification.tasks import send_password_reset_email


class PasswordResetVerificationSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        send_password_reset_email.delay(email=validated_data["email"])
        return validated_data


class PasswordResetVerificationCheckSerializer(BaseCheckSerializer):
    model = PasswordResetVerification


class PasswordResetSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()
    consent = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def fail_email(self) -> NoReturn:
        raise serializers.ValidationError(
            {
                "email": gettext(
                    "This e-mail could not be verified. Please provide"
                    " a validated e-mail address."
                )
            }
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        email, password = validated_data["email"], validated_data["password"]
        try:
            user = User.objects.get(email=email)
            if not user.has_usable_password():
                # This block should be unreachable in normal circumstances since
                # this condition is also checked before sending code to email.
                # However, if the consent is generated somehow this check
                # ensures the password validation still fails.
                raise ValueError
        except (User.DoesNotExist, ValueError):
            self.fail_email()

        try:
            validate_password(password, user=user)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        verification = PasswordResetVerification.objects.get_with_consent(
            email, validated_data["consent"], user=user
        )

        if verification is None:
            self.fail_email()

        verification.completed_at = timezone.now()
        verification.save(update_fields=["completed_at", "updated_at"])
        verification.null_others()

        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])
        user.revoke_other_tokens(self.context["request"].auth)

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.password_change_notice
        )
        transaction.on_commit(send_notice)
        return validated_data
