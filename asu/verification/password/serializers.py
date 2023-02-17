from django.db import transaction

from rest_framework import serializers

from asu.auth.models import User
from asu.verification.models import PasswordResetVerification
from asu.verification.registration.serializers import BaseCheckSerializer


class PasswordResetVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetVerification
        fields = ("email",)

    def validate_email(self, email):
        return User.objects.normalize_email(email)

    @transaction.atomic
    def create(self, validated_data):
        try:
            validated_data["user"] = User.objects.get(
                email=validated_data["email"]
            )
        except User.DoesNotExist:
            return validated_data

        verification = super().create(validated_data)
        transaction.on_commit(verification.send_email)
        return verification


class PasswordResetVerificationCheckSerializer(BaseCheckSerializer):
    model = PasswordResetVerification
