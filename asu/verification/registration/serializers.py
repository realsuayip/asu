from typing import Any

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models.functions import Now
from django.utils.translation import gettext

from rest_framework import serializers

from asu.auth.models import User
from asu.auth.serializers.user import AuthSerializer, validate_username_constraints
from asu.verification.models.registration import RegistrationVerification
from asu.verification.serializers import (
    VerificationCheckSerializer,
    VerificationSendSerializer,
)
from asu.verification.tasks import send_registration_email


class RegistrationVerificationSendSerializer(VerificationSendSerializer):
    def send(self, *, email: str, uid: str) -> None:
        send_registration_email.delay(email=email, uid=uid)


class RegistrationVerificationCheckSerializer(VerificationCheckSerializer):
    model = RegistrationVerification


class UserCreateSerializer(serializers.ModelSerializer[User]):
    auth = AuthSerializer(source="_auth_dict", read_only=True)

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> User:
        pk = validated_data.pop("id")
        try:
            verification = (
                RegistrationVerification.objects.eligible()
                .only("pk", "email")
                .select_for_update()
                .get(pk=pk)
            )
        except RegistrationVerification.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "id": gettext(
                        "This e-mail could not be verified."
                        " Please provide a validated e-mail address."
                    )
                }
            )

        password = validated_data.pop("password")
        user = User(email=verification.email, **validated_data)
        validate_username_constraints(user)

        try:
            validate_password(password, user=user)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        user.set_password(password)
        user.save(force_insert=True)
        verification.user = user
        verification.completed_at = Now()
        verification.save(update_fields=["user", "completed_at", "updated_at"])
        verification.null_others()
        user._auth_dict = user.issue_token()  # type: ignore[attr-defined]
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "username",
            "password",
            "birth_date",
            "language",
            "auth",
            "created_at",
        )
        read_only_fields = ("email", "auth", "created_at")
        extra_kwargs = {"password": {"write_only": True}}
