from typing import Any

from rest_framework import serializers

from asu.auth.models import User
from asu.verification.models.registration import RegistrationVerification
from asu.verification.serializers import BaseCheckSerializer
from asu.verification.tasks import send_registration_email


class RegistrationSerializer(serializers.Serializer[dict[str, Any]]):
    """
    Create registration verification object and send the email containing code.
    """

    email = serializers.EmailField()

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        send_registration_email.delay(email=validated_data["email"])
        return validated_data


class RegistrationCheckSerializer(BaseCheckSerializer):
    model = RegistrationVerification
