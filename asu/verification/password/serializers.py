from typing import Any

from rest_framework import serializers

from asu.auth.models import User
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
