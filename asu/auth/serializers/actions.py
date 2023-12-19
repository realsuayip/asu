from __future__ import annotations

import functools
from typing import Any, NoReturn, TypeVar

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from django_stubs_ext import WithAnnotations
from drf_spectacular.utils import extend_schema_field

from asu.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from asu.auth.serializers.user import UserPublicReadSerializer
from asu.utils import messages
from asu.verification.models import PasswordResetVerification

T = TypeVar("T", bound=models.Model)

user_fields = (
    "id",
    "display_name",
    "username",
    "profile_picture",
    "description",
    "is_private",
    "url",
)
RelatedUserField = UserPublicReadSerializer(
    read_only=True,
    fields=user_fields,
    ref_name="RelatedUser",
)
ManyRelatedUserField = UserPublicReadSerializer(
    many=True,
    read_only=True,
    fields=user_fields,
    ref_name="ManyRelatedUser",
)


class PasswordResetSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()
    consent = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_email(self, email: str) -> str:
        return User.objects.normalize_email(email)

    def fail_email(self) -> NoReturn:
        raise serializers.ValidationError(
            {"email": gettext("This e-mail could not be verified.")}
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        request = self.context["request"]
        password = validated_data["password"]
        email = validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.fail_email()

        try:
            validate_password(password, user=user)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"password": err.messages})

        verification = PasswordResetVerification.objects.get_with_consent(
            email, validated_data["consent"], user=user
        )

        if verification is None:
            self.fail_email()

        verification.date_completed = timezone.now()
        verification.save(update_fields=["date_completed", "date_modified"])
        verification.null_others()

        user.set_password(password)
        user.save(update_fields=["password", "date_modified"])
        user.revoke_other_tokens(request.auth)

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.password_change_notice
        )
        transaction.on_commit(send_notice)
        return validated_data


class UserRelationMixin:
    class Meta:
        fields = ("from_user", "to_user")
        extra_kwargs = {
            "from_user": {"write_only": True},
            "to_user": {"write_only": True},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["from_user"] == attrs["to_user"]:
            raise PermissionDenied
        return attrs

    def get_rels(
        self, model: type[T], *, from_user: User, to_user: User
    ) -> QuerySet[T]:
        # Given m2m through model, return queryset
        # containing objects for both directions
        return model._default_manager.filter(
            (Q(from_user=from_user) & Q(to_user=to_user))
            | (Q(to_user=from_user) & Q(from_user=to_user))
        )


class BlockSerializer(UserRelationMixin, serializers.ModelSerializer[UserBlock]):
    class Meta(UserRelationMixin.Meta):
        model = UserBlock

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> UserBlock:
        # If there is a follow relationship between
        # users, delete it before blocking.
        self.get_rels(UserFollow, **validated_data).delete()
        self.get_rels(UserFollowRequest, **validated_data).update(
            status=UserFollowRequest.Status.REJECTED
        )
        block, _ = UserBlock.objects.get_or_create(**validated_data)
        return block


class FollowSerializer(
    UserRelationMixin, serializers.ModelSerializer[UserFollow | UserFollowRequest]
):
    class Meta(UserRelationMixin.Meta):
        model = UserFollow

    def create(self, validated_data: dict[str, Any]) -> UserFollow | UserFollowRequest:
        from_user: User = validated_data["from_user"]
        to_user: User = validated_data["to_user"]

        # If users block each other in any
        # direction, following is not allowed.
        blocks = self.get_rels(UserBlock, **validated_data)
        if blocks.exists():
            raise PermissionDenied

        if to_user.is_private:
            follow_request, _ = from_user.send_follow_request(to_user=to_user)
            return follow_request

        follow, _ = from_user.add_following(to_user=to_user)
        return follow


class FollowRequestSerializer(serializers.ModelSerializer[UserFollowRequest]):
    from_user = RelatedUserField
    status = serializers.ChoiceField(
        choices=[
            UserFollowRequest.Status.REJECTED,
            UserFollowRequest.Status.APPROVED,
        ],
        write_only=True,
    )

    class Meta:
        model = UserFollowRequest
        fields = ("from_user", "status", "url")
        extra_kwargs = {"url": {"view_name": "api:auth:follow-request-detail"}}

    @transaction.atomic
    def update(
        self, instance: UserFollowRequest, validated_data: dict[str, Any]
    ) -> UserFollowRequest:
        instance = super().update(instance, validated_data)
        if instance.is_approved:
            instance.bond()
        return instance


class UserFollowersSerializer(serializers.ModelSerializer[UserFollow]):
    from_user = RelatedUserField

    class Meta:
        model = UserFollow
        fields = ("from_user",)

    def to_representation(self, instance: UserFollow) -> Any:
        return super().to_representation(instance).pop("from_user")


class UserFollowingSerializer(serializers.ModelSerializer[UserFollow]):
    to_user = RelatedUserField

    class Meta:
        model = UserFollow
        fields = ("to_user",)

    def to_representation(self, instance: UserFollow) -> Any:
        return super().to_representation(instance).pop("to_user")


class UserBlockedSerializer(UserFollowingSerializer):
    class Meta:
        model = UserBlock
        fields = ("to_user",)


class TicketSerializer(serializers.Serializer[dict[str, Any]]):
    ticket = serializers.CharField(read_only=True)

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        user = self.context["request"].user
        validated_data["ticket"] = user.create_websocket_ticket()
        return validated_data


class ProfilePictureEditSerializer(serializers.ModelSerializer[User]):
    class Meta:
        fields = ("profile_picture",)
        model = User
        extra_kwargs = {"profile_picture": {"required": True}}

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        image = validated_data["profile_picture"]
        instance.set_profile_picture(image)
        return instance


rels = {
    "following",
    "followed_by",
    "follow_request_sent",
    "follow_request_received",
    "blocking",
    "blocked_by",
}


class UserWithRelationSerializer(serializers.ModelSerializer[User]):
    relations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "display_name", "relations")

    @extend_schema_field(
        serializers.ListField(
            child=serializers.ChoiceField(choices=rels),
            help_text="May contain multiple relations.",
        )
    )
    def get_relations(self, obj: WithAnnotations[User]) -> list[str]:
        return [name for name, exists in obj.rels.items() if exists]


class RelationSerializer(serializers.Serializer[dict[str, Any]]):
    results = UserWithRelationSerializer(many=True)


class DeactivationSerializer(serializers.Serializer[dict[str, Any]]):
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_password(self, password: str) -> str:
        user = self.context["request"].user
        if not user.check_password(password):
            raise serializers.ValidationError("Your password was not correct.")
        return password

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        user = self.context["request"].user
        user.deactivate()
        return validated_data
