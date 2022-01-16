from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from zeynep.verification.models import RegistrationVerification, code_validator


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Create registration verification object and
    send the email containing code.
    """

    class Meta:
        model = RegistrationVerification
        fields = ("email",)

    @transaction.atomic
    def create(self, validated_data):
        verification = super().create(validated_data)
        # todo send mail here
        return verification


class RegistrationCheckSerializer(serializers.Serializer):  # noqa
    """
    Check the registration verification, verify it and
    return corresponding consent.
    """

    email = serializers.EmailField(label=_("email"))
    code = serializers.CharField(
        label=_("code"),
        max_length=6,
        validators=[code_validator],
    )
    consent = serializers.CharField(read_only=True)

    def create(self, validated_data):
        try:
            verification = RegistrationVerification.objects.verifiable().get(
                **validated_data
            )
        except RegistrationVerification.DoesNotExist:
            raise NotFound

        verification.date_verified = timezone.now()
        verification.save(update_fields=["date_verified"])
        validated_data["consent"] = verification.create_consent()
        return validated_data


class RegistrationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = RegistrationSerializer

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationCheckSerializer,
    )
    def check(self, request):
        serializer = RegistrationCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=200)
