from django.db import transaction
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from zeynep.auth.models import User
from zeynep.verification.models.registration import RegistrationVerification
from zeynep.verification.serializers import BaseCheckSerializer


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Create registration verification object and
    send the email containing code.
    """

    class Meta:
        model = RegistrationVerification
        fields = ("email",)

    def validate_email(self, email):  # noqa
        email = User.objects.normalize_email(email)
        user = User.objects.filter(email=email)

        if user.exists():
            raise ValidationError(gettext("This e-mail is already in use."))

        return email

    @transaction.atomic
    def create(self, validated_data):
        verification = super().create(validated_data)
        verification.send_email()
        return verification


class RegistrationCheckSerializer(BaseCheckSerializer):  # noqa
    model = RegistrationVerification
