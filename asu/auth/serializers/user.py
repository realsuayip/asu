from collections.abc import Sequence
from typing import Any

import django.core.exceptions

from rest_framework import serializers

from asu.auth.models import User
from asu.auth.models.user import USERNAME_CONSTRAINTS
from asu.core.utils.rest import DynamicFieldsMixin


def validate_username_constraints(instance: User) -> None:
    for constraint in USERNAME_CONSTRAINTS:
        try:
            constraint.validate(User, instance)  # type: ignore[attr-defined]
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"username": err.messages})


class UserPublicReadSerializer(DynamicFieldsMixin, serializers.ModelSerializer[User]):
    following_count = serializers.IntegerField()
    follower_count = serializers.IntegerField()
    profile_picture = serializers.ImageField(source="get_profile_picture")

    class Meta:
        model = User
        fields: Sequence[str] = (
            "id",
            "display_name",
            "username",
            "profile_picture",
            "is_private",
            "description",
            "website",
            "following_count",
            "follower_count",
            "created_at",
        )


class UserSerializer(DynamicFieldsMixin, serializers.ModelSerializer[User]):
    profile_picture = serializers.ImageField(source="get_profile_picture")
    two_factor_enabled = serializers.BooleanField()

    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "email",
            "description",
            "website",
            "profile_picture",
            "language",
            "birth_date",
            "is_private",
            "allows_receipts",
            "allows_all_messages",
            "two_factor_enabled",
            "created_at",
        )
        read_only_fields = (
            "id",
            "email",
            "profile_picture",
            "two_factor_enabled",
            "created_at",
        )

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        # This method is overridden so that `validate_username_constraints`
        # could be called, triggering related database constraints.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        validate_username_constraints(instance)
        instance.save(update_fields={*validated_data, "updated_at"})
        return instance


class AuthSerializer(serializers.Serializer[dict[str, Any]]):
    access_token = serializers.CharField()
    token_type = serializers.ChoiceField(choices=["Bearer"])
    expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField()
    scope = serializers.CharField()
