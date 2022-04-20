import django.core.validators
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers

from zeynep.auth.models import User
from zeynep.utils.rest import DynamicFieldsMixin
from zeynep.verification.models import RegistrationVerification


class UserPublicReadSerializer(
    DynamicFieldsMixin, serializers.HyperlinkedModelSerializer
):
    following_count = serializers.IntegerField()
    follower_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "date_joined",
            "is_private",
            "description",
            "website",
            "following_count",
            "follower_count",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "username",
            "gender",
            "birth_date",
            "date_joined",
            "is_private",
            "description",
            "website",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}
        read_only_fields = ("email", "date_joined")


class UserCreateSerializer(serializers.HyperlinkedModelSerializer):
    consent = serializers.CharField(write_only=True)
    password = serializers.CharField(
        max_length=256,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_email(self, email):  # noqa
        return User.objects.normalize_email(email)

    @transaction.atomic
    def create(self, validated_data):
        consent = validated_data.pop("consent")
        email = validated_data["email"]

        verification = RegistrationVerification.objects.get_with_consent(
            email, consent
        )

        if verification is None:
            raise serializers.ValidationError(
                {
                    "email": gettext(
                        "This e-mail could not be verified."
                        " Please provide a validated e-mail address."
                    )
                }
            )

        password = validated_data.pop("password")
        user = User(**validated_data)

        try:
            validate_password(password, user=user)
        except django.core.validators.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        user.set_password(password)
        user.save()
        verification.user = user
        verification.date_completed = timezone.now()
        verification.save(update_fields=["user", "date_completed"])
        verification.null_others()
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "username",
            "password",
            "gender",
            "birth_date",
            "consent",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}
