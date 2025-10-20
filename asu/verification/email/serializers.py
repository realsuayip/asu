from typing import Any

from django.db import transaction
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.auth.models import User
from asu.core.utils import messages
from asu.verification.models import EmailVerification
from asu.verification.serializers import BaseCheckSerializer
from asu.verification.tasks import send_email_change_email


class EmailSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        send_email_change_email.delay(
            user_id=self.context["request"].user.pk,
            email=validated_data["email"],
        )
        return validated_data


class EmailCheckSerializer(BaseCheckSerializer):
    consent = None

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        user = self.context["request"].user

        try:
            verification = EmailVerification.objects.verifiable().get(
                user=user, **validated_data
            )
        except EmailVerification.DoesNotExist:
            raise NotFound(messages.BAD_VERIFICATION_CODE)

        verification.date_verified = timezone.now()
        verification.save(update_fields=["date_verified", "date_modified"])
        verification.null_others()

        user.email = verification.email
        user.save(update_fields=["email", "date_modified"])
        return validated_data
