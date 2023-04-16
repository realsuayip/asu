from typing import Any, Type

from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.auth.models import User
from asu.verification.models.base import ConsentVerification, code_validator


class BaseCheckSerializer(
    serializers.Serializer[ConsentVerification | dict[str, Any]]
):
    """
    Check the verification, verify it and
    return corresponding consent.
    """

    model: Type[ConsentVerification]

    email = serializers.EmailField(label=_("email"))
    code = serializers.CharField(
        label=_("code"),
        max_length=6,
        validators=[code_validator],
    )
    consent: serializers.CharField | None = serializers.CharField(
        read_only=True,
        help_text="This consent value will be needed while you perform the"
        " related action. It will expire after some time.",
    )

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        try:
            verification = self.model.objects.verifiable().get(
                **validated_data
            )
        except self.model.DoesNotExist:
            raise NotFound

        verification.date_verified = timezone.now()
        verification.save(update_fields=["date_verified", "date_modified"])
        validated_data["consent"] = verification.create_consent()
        return validated_data


class EmailMixin:
    def validate_email(self, email: str) -> str:
        email = User.objects.normalize_email(email)
        user = User.objects.filter(email=email)

        if user.exists():
            raise serializers.ValidationError(
                gettext("This e-mail is already in use.")
            )

        return email
