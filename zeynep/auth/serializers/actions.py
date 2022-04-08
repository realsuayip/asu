import django.core.validators
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

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

    @transaction.atomic
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

    def validate(self, attrs):
        if attrs["from_user"] == attrs["to_user"]:
            raise PermissionDenied
        return attrs

    def get_rels(self, model, *, from_user, to_user):  # noqa
        # Given m2m through model, return queryset
        # containing objects for both directions
        return model.objects.filter(
            (Q(from_user=from_user) & Q(to_user=to_user))
            | (Q(to_user=from_user) & Q(from_user=to_user))
        )

    @transaction.atomic
    def create(self, validated_data):
        # If there is a follow relationship between
        # users, delete it before blocking.
        self.get_rels(UserFollow, **validated_data).delete()
        return UserBlock.objects.get_or_create(**validated_data)


class FollowSerializer(BlockSerializer):
    class Meta(BlockSerializer.Meta):
        model = UserFollow

    def create(self, validated_data):
        # If users block each other in any
        # direction, following is not allowed.
        blocks = self.get_rels(UserBlock, **validated_data)
        if blocks.exists():
            raise PermissionDenied
        return UserFollow.objects.get_or_create(**validated_data)
