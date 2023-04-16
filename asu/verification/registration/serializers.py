from typing import Any

from django.db import transaction

from rest_framework import serializers

from asu.verification.models.registration import RegistrationVerification
from asu.verification.serializers import BaseCheckSerializer, EmailMixin


class RegistrationSerializer(
    EmailMixin, serializers.ModelSerializer[RegistrationVerification]
):
    """
    Create registration verification object and
    send the email containing code.
    """

    class Meta:
        model = RegistrationVerification
        fields = ("email",)

    @transaction.atomic
    def create(
        self, validated_data: dict[str, Any]
    ) -> RegistrationVerification:
        verification = super().create(validated_data)
        transaction.on_commit(verification.send_email)
        return verification


class RegistrationCheckSerializer(BaseCheckSerializer):
    model = RegistrationVerification
