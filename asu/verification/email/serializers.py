from typing import Any

from django.db import transaction
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.verification.models import EmailVerification
from asu.verification.serializers import BaseCheckSerializer, EmailMixin


class EmailSerializer(EmailMixin, serializers.ModelSerializer[EmailVerification]):
    class Meta:
        model = EmailVerification
        fields = ("email",)

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> EmailVerification:
        validated_data["user"] = self.context["request"].user
        verification = super().create(validated_data)
        transaction.on_commit(verification.send_email)
        return verification


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
            raise NotFound

        verification.date_verified = timezone.now()
        verification.save(update_fields=["date_verified", "date_modified"])
        verification.null_others()

        user.email = verification.email
        user.save(update_fields=["email", "date_modified"])
        return validated_data
