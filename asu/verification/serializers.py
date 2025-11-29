import uuid
from typing import Any, ClassVar

from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.auth.models import User
from asu.core.utils import messages
from asu.verification.models.base import ConsentVerification, code_validator


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

    model: ClassVar[type[ConsentVerification]]

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        pk, code = validated_data["id"], validated_data["code"]
        try:
            verification = (
                self.model.objects.verifiable()
                .only("pk")
                .select_for_update()
                .get(pk=pk, code=code)
            )
        except self.model.DoesNotExist:
            raise NotFound(messages.BAD_VERIFICATION_CODE)

        verification.verified_at = Now()
        verification.save(update_fields=["verified_at", "updated_at"])
        return validated_data
