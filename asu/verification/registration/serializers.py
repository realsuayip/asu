from typing import Any

from django.db import transaction
from django.db.models import Q

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.auth.models import User
from asu.auth.serializers.user import AuthSerializer, validate_username_constraints
from asu.core.utils import messages
from asu.verification.models.registration import RegistrationVerification
from asu.verification.serializers import (
    VerificationSendSerializer,
    VerificationVerifySerializer,
)
from asu.verification.tasks import send_registration_email


class RegistrationVerificationSendSerializer(VerificationSendSerializer):
    def send(self, *, email: str, uid: str) -> None:
        send_registration_email.delay(email=email, uid=uid)


class RegistrationVerificationVerifySerializer(VerificationVerifySerializer):
    model = RegistrationVerification


class UserCreateSerializer(serializers.ModelSerializer[User]):
    id = serializers.UUIDField()
    auth = AuthSerializer(source="_auth_dict", read_only=True)

    @transaction.atomic(durable=True)
    def create(self, validated_data: dict[str, Any]) -> User:
        pk = validated_data.pop("id")
        try:
            verification = (
                RegistrationVerification.objects.eligible()
                .only("pk", "email")
                .get(pk=pk)
            )
        except RegistrationVerification.DoesNotExist:
            raise NotFound(messages.BAD_VERIFICATION_ID)

        password = validated_data.pop("password")
        user = User(email=verification.email, **validated_data)
        user.set_validated_password(password)
        validate_username_constraints(user)
        user.save(force_insert=True)

        if not verification.complete(
            lock_query=Q(email__iexact=verification.email),
            user=user,
        ):
            raise NotFound(messages.BAD_VERIFICATION_ID)

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
