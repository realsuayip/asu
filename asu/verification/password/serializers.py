from typing import Any

from django.db import transaction

from rest_framework import serializers

from asu.auth.models import User
from asu.verification.models import PasswordResetVerification
from asu.verification.serializers import BaseCheckSerializer


class PasswordResetVerificationSerializer(
    serializers.ModelSerializer[PasswordResetVerification]
):
    class Meta:
        model = PasswordResetVerification
        fields = ("email",)

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> PasswordResetVerification:
        try:
            validated_data["user"] = User.objects.get(email=validated_data["email"])
        except User.DoesNotExist:
            return validated_data  # type: ignore[return-value]

        verification = super().create(validated_data)
        transaction.on_commit(verification.send_email)
        return verification


class PasswordResetVerificationCheckSerializer(BaseCheckSerializer):
    model = PasswordResetVerification
