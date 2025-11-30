import uuid
from typing import Any, ClassVar

from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.auth.models import User
from asu.core.utils import messages
from asu.verification.models.base import ExtendedVerification, code_validator


class VerificationSendSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        uid = uuid.uuid7()
        self.send(email=validated_data["email"], uid=uid.hex)
        validated_data["id"] = uid
        return validated_data

    def send(self, *, email: str, uid: str) -> None:
        raise NotImplementedError


class VerificationCheckSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField(write_only=True)
    code = serializers.CharField(
        label=_("code"),
        validators=[code_validator],
        write_only=True,
    )

    model: ClassVar[type[ExtendedVerification]]

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        pk, code = validated_data["id"], validated_data["code"]
        updated = (
            self.model.objects.verifiable()
            .filter(pk=pk, code=code)
            .update(verified_at=Now(), updated_at=Now())
        )
        if not updated:
            raise NotFound(messages.BAD_VERIFICATION_CODE)
        return validated_data
