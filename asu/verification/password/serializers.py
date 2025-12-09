import functools
from typing import Any

from django.db import transaction
from django.db.models import Q

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.core.utils import messages
from asu.verification.models import PasswordResetVerification
from asu.verification.serializers import (
    VerificationSendSerializer,
    VerificationVerifySerializer,
)
from asu.verification.tasks import send_password_reset_email


class PasswordResetVerificationSendSerializer(VerificationSendSerializer):
    def send(self, *, email: str, uid: str) -> None:
        send_password_reset_email.delay(uid=uid, email=email)


class PasswordResetVerificationVerifySerializer(VerificationVerifySerializer):
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
                    "email",
                    "user_id",
                    "user__username",
                    "user__email",
                    "user__password",
                )
                .get(pk=validated_data["id"])
            )
        except PasswordResetVerification.DoesNotExist:
            verification = None
        if (
            verification is None
            or (user := verification.user) is None
            or verification.email.lower() != verification.user.email.lower()
            or not user.has_usable_password()
        ):
            # Under normal circumstances, it isn't possible to acquire valid id
            # while having 'unusable' password. We still do this check in case
            # unusable password is set after acquiring id.
            raise NotFound(messages.BAD_VERIFICATION_ID)
        user.set_validated_password(validated_data["password"])

        if not verification.complete(lock_query=Q(user_id=verification.user_id)):
            raise NotFound(messages.BAD_VERIFICATION_ID)

        user.save(update_fields=["password", "updated_at"])
        user.revoke_other_tokens()
        user.revoke_all_sessions()

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.PASSWORD_CHANGE_NOTICE
        )
        transaction.on_commit(send_notice)
        return validated_data
