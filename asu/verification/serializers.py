from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from asu.verification.models.base import code_validator


class BaseCheckSerializer(serializers.Serializer):  # noqa
    """
    Check the verification, verify it and
    return corresponding consent.
    """

    model = None

    email = serializers.EmailField(label=_("email"))
    code = serializers.CharField(
        label=_("code"),
        max_length=6,
        validators=[code_validator],
    )
    consent = serializers.CharField(
        read_only=True,
        help_text="This consent value will be needed while you perform the"
        " related action. It will expire after some time.",
    )

    def create(self, validated_data):
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
