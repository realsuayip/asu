from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound

from zaida.verification.models import EmailVerification
from zaida.verification.registration.serializers import RegistrationSerializer
from zaida.verification.serializers import BaseCheckSerializer


class EmailSerializer(RegistrationSerializer):
    class Meta:
        model = EmailVerification
        fields = ("email",)

    @transaction.atomic
    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        verification = super().create(validated_data)
        return verification


class EmailCheckSerializer(BaseCheckSerializer):  # noqa
    consent = None

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        try:
            verification = EmailVerification.objects.verifiable().get(
                user=user, **validated_data
            )
        except EmailVerification.DoesNotExist:
            raise NotFound

        verification.date_verified = timezone.now()
        verification.save(update_fields=["date_verified", "date_modified"])
        verification.null_others()

        user.email = verification.email
        user.save(update_fields=["email", "date_modified"])
        return validated_data
