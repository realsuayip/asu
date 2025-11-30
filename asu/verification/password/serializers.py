import functools
from typing import Any

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models.functions import Now

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.core.utils import messages
from asu.verification.models import PasswordResetVerification
from asu.verification.serializers import (
    VerificationCheckSerializer,
    VerificationSendSerializer,
)
from asu.verification.tasks import send_password_reset_email


class PasswordResetVerificationSendSerializer(VerificationSendSerializer):
    def send(self, *, email: str, uid: str) -> None:
        send_password_reset_email.delay(uid=uid, email=email)


class PasswordResetVerificationCheckSerializer(VerificationCheckSerializer):
    model = PasswordResetVerification


class PasswordResetSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField(write_only=True)
    password = serializers.CharField(write_only=True)

    @transaction.atomic(durable=True)
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        try:
            verification = (
                PasswordResetVerification.objects.eligible()
                .select_related("user")
                .only(
                    "id",
                    "user_id",
                    "user__username",
                    "user__email",
                    "user__password",
                )
                .select_for_update(of=("self",))
                .get(pk=validated_data["id"])
            )
        except PasswordResetVerification.DoesNotExist:
            verification = None
        if (
            verification is None
            or (user := verification.user) is None
            or not user.has_usable_password()
        ):
            # Under normal circumstances, it is not possible to acquire ident
            # while having 'unusable' password. We still do this check in case
            # unusable password is set after acquiring ident.
            raise NotFound(messages.BAD_VERIFICATION_ID)

        # Validate password
        password = validated_data["password"]
        try:
            validate_password(password, user=user)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        verification.completed_at = Now()
        verification.save(update_fields=["completed_at", "updated_at"])
        verification.null_others()

        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])
        user.revoke_other_tokens()
        user.revoke_all_sessions()

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.PASSWORD_CHANGE_NOTICE
        )
        transaction.on_commit(send_notice)
        return validated_data
