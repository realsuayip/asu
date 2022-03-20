import django.core.validators
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from zeynep.auth.models import User, UserBlock, UserFollow
from zeynep.verification.models import PasswordResetVerification


class PasswordResetSerializer(serializers.Serializer):  # noqa
    email = serializers.EmailField()
    consent = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_email(self, email):  # noqa
        return User.objects.normalize_email(email)

    def create(self, validated_data):
        password = validated_data["password"]
        email = validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFound

        try:
            validate_password(password, user=user)
        except django.core.validators.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        verification = PasswordResetVerification.objects.get_with_consent(
            email, validated_data["consent"], user=user
        )

        if verification is None:
            raise serializers.ValidationError(
                {"email": gettext("This e-mail could not be verified.")}
            )

        verification.date_completed = timezone.now()
        verification.save(update_fields=["date_completed"])
        verification.null_others()

        user.set_password(password)
        user.save(update_fields=["password"])
        return validated_data


class BlockSerializer(serializers.ModelSerializer):
    to_user = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.active(),
        write_only=True,
    )

    class Meta:
        model = UserBlock
        fields = ("from_user", "to_user")
        extra_kwargs = {"from_user": {"write_only": True}}

    def create(self, validated_data):
        return self.Meta.model.objects.get_or_create(**validated_data)


class FollowSerializer(BlockSerializer):
    class Meta(BlockSerializer.Meta):
        model = UserFollow
