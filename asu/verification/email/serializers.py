from typing import Any

from django.db import transaction
from django.db.models.functions import Now

from rest_framework.exceptions import NotFound

from asu.core.utils import messages
from asu.verification.models import EmailVerification
from asu.verification.serializers import (
    VerificationSendSerializer,
    VerificationVerifySerializer,
)
from asu.verification.tasks import send_email_change_email


class EmailVerificationSendSerializer(VerificationSendSerializer):
    def send(self, *, email: str, uid: str) -> None:
        send_email_change_email.delay(
            user_id=self.context["request"].user.pk,
            email=email,
            uid=uid,
        )


class ChangeEmailSerializer(VerificationVerifySerializer):
    @transaction.atomic(durable=True)
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        user = self.context["request"].user
        pk, code = validated_data["id"], validated_data["code"]

        try:
            verification = (
                EmailVerification.objects.verifiable()
                .only("pk", "email")
                .select_for_update()
                .get(pk=pk, code=code, user=user)
            )
        except EmailVerification.DoesNotExist:
            raise NotFound(messages.BAD_VERIFICATION_CODE)

        verification.verified_at = Now()
        verification.save(update_fields=["verified_at", "updated_at"])
        verification.null_others()

        user.email = verification.email
        user.save(update_fields=["email", "updated_at"])
        return validated_data
