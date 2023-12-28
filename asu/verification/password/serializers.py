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
            user = User.objects.get(email=validated_data["email"])
            if not user.has_usable_password():
                # Consistent with Django behavior, users with unusable
                # passwords may not reset their passwords.
                raise ValueError
        except (User.DoesNotExist, ValueError):
            return validated_data  # type: ignore[return-value]

        validated_data["user"] = user
        verification = super().create(validated_data)
        transaction.on_commit(verification.send_email)
        return verification


class PasswordResetVerificationCheckSerializer(BaseCheckSerializer):
    model = PasswordResetVerification
