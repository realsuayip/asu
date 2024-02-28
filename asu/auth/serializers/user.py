from typing import Any

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers

from asu.auth.models import User
from asu.auth.models.user import USERNAME_CONSTRAINTS
from asu.utils.rest import DynamicFieldsMixin
from asu.verification.models import RegistrationVerification


def validate_username_constraints(instance: User) -> None:
    for constraint in USERNAME_CONSTRAINTS:
        try:
            constraint.validate(User, instance)  # type: ignore[attr-defined]
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"username": err.messages})


class UserPublicReadSerializer(
    DynamicFieldsMixin, serializers.HyperlinkedModelSerializer
):
    following_count = serializers.IntegerField()
    follower_count = serializers.IntegerField()
    profile_picture = serializers.ImageField(source="get_profile_picture")

    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "profile_picture",
            "date_joined",
            "is_private",
            "description",
            "website",
            "following_count",
            "follower_count",
            "url",
        )
        extra_kwargs = {"url": {"view_name": "api:auth:user-detail"}}


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
            "language",
            "url",
        )
        extra_kwargs = {"url": {"view_name": "api:auth:user-detail"}}
        read_only_fields = ("email", "date_joined")

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        # This method is overridden so that `validate_username_constraints`
        # could be called, triggering related database constraints.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        validate_username_constraints(instance)
        instance.save(update_fields=validated_data.keys())
        return instance


class AuthSerializer(serializers.Serializer[dict[str, Any]]):
    access_token = serializers.CharField()
    token_type = serializers.ChoiceField(choices=["Bearer"])
    expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField()
    scope = serializers.CharField()


class UserCreateSerializer(serializers.HyperlinkedModelSerializer):
    consent = serializers.CharField(write_only=True)
    password = serializers.CharField(
        max_length=256,
        write_only=True,
        style={"input_type": "password"},
    )
    auth = AuthSerializer(source="_auth_dict", read_only=True)

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> User:
        consent = validated_data.pop("consent")
        email = validated_data["email"]

        verification = RegistrationVerification.objects.get_with_consent(email, consent)

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
        validate_username_constraints(user)

        try:
            validate_password(password, user=user)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        user.set_password(password)
        user.save()
        verification.user = user
        verification.date_completed = timezone.now()
        verification.save(update_fields=["user", "date_completed", "date_modified"])
        verification.null_others()
        user._auth_dict = user.issue_token()  # type: ignore[attr-defined]
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
            "language",
            "consent",
            "auth",
            "url",
        )
        extra_kwargs = {"url": {"view_name": "api:auth:user-detail"}}
