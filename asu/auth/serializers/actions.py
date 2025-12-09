import functools
from typing import Any, TypeVar, cast

from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from drf_spectacular.utils import extend_schema_field

from asu.auth.models import (
    User,
    UserBlock,
    UserDeactivation,
    UserFollow,
    UserFollowRequest,
)
from asu.auth.serializers.user import UserPublicReadSerializer
from asu.core.utils import messages
from asu.core.utils.rest import ContextDefault
from asu.core.utils.typing import UserRequest

T = TypeVar("T", bound=models.Model)

user_fields = (
    "id",
    "display_name",
    "username",
    "profile_picture",
    "description",
    "is_private",
)
RelatedUserField = UserPublicReadSerializer(
    read_only=True,
    fields=user_fields,
    ref_name="RelatedUser",
)


class PasswordChangeSerializer(serializers.Serializer[dict[str, str]]):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    @transaction.atomic(durable=True)
    def create(self, validated_data: dict[str, str]) -> dict[str, str]:
        request: UserRequest = self.context["request"]
        user = request.user

        if not user.check_password(validated_data["old_password"]):
            raise serializers.ValidationError(
                {"old_password": gettext("Your password was not correct.")}
            )

        user.set_validated_password(validated_data["new_password"], key="new_password")
        user.save(update_fields=["password", "updated_at"])
        user.revoke_other_tokens(request.auth)

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.PASSWORD_CHANGE_NOTICE
        )
        transaction.on_commit(send_notice)
        return validated_data


class CreateRelationSerializer(serializers.Serializer[dict[str, Any]]):
    from_user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    to_user = serializers.HiddenField(default=ContextDefault("to_user"))

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["from_user"] == attrs["to_user"]:
            raise PermissionDenied
        return attrs


class BlockSerializer(CreateRelationSerializer):
    def get_rels(
        self, model: type[T], *, from_user: User, to_user: User
    ) -> QuerySet[T]:
        # Given m2m through model, return queryset
        # containing objects for both directions
        return model._default_manager.filter(
            (Q(from_user=from_user) & Q(to_user=to_user))
            | (Q(to_user=from_user) & Q(from_user=to_user))
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        _, created = UserBlock.objects.get_or_create(**validated_data)
        if created:
            # If there is a follow relationship between
            # users, delete them during blocking.
            self.get_rels(UserFollow, **validated_data).delete()
            self.get_rels(UserFollowRequest, **validated_data).filter(
                status=UserFollowRequest.Status.PENDING
            ).update(status=UserFollowRequest.Status.REJECTED)
        return validated_data


class FollowStatus(models.TextChoices):
    FOLLOWING = "following", "Following"
    REQUEST_SENT = "follow_request_sent", "Follow Request Sent"


class FollowSerializer(CreateRelationSerializer):
    status = serializers.ChoiceField(choices=FollowStatus.choices, read_only=True)

    def create_relations(self, from_user: User, to_user: User) -> FollowStatus:
        if to_user.is_private:
            if from_user.is_following(to_user):
                return FollowStatus.FOLLOWING

            from_user.send_follow_request(to_user=to_user)
            return FollowStatus.REQUEST_SENT

        from_user.add_following(to_user=to_user)
        return FollowStatus.FOLLOWING

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        # At this point, we are certain that no blocking relations exist
        # since `get_object()` checks for that and returns 403. So, we can
        # safely proceed to creating follow relations.
        return {"status": self.create_relations(**validated_data)}


class FollowRequestSerializer(serializers.ModelSerializer[UserFollowRequest]):
    from_user = RelatedUserField

    class Meta:
        model = UserFollowRequest
        fields = ("id", "from_user")


class UserConnectionSerializer(UserPublicReadSerializer):
    class Meta(UserPublicReadSerializer.Meta):
        fields = (
            "id",
            "display_name",
            "username",
            "profile_picture",
            "description",
            "is_private",
        )


class ProfilePictureEditSerializer(serializers.ModelSerializer[User]):
    class Meta:
        fields = ("profile_picture",)
        model = User
        extra_kwargs = {"profile_picture": {"required": True}}

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        image = validated_data["profile_picture"]
        instance.set_profile_picture(image)
        return instance


rels = (
    "following",
    "followed_by",
    "follow_request_sent",
    "follow_request_received",
    "blocking",
    "blocked_by",
)


class UserWithRelationSerializer(serializers.ModelSerializer[User]):
    relations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "relations")

    @extend_schema_field(
        serializers.ListField(
            child=serializers.ChoiceField(choices=rels),
            help_text="May contain multiple relations.",
        )
    )
    def get_relations(self, obj: User) -> list[str]:
        return [name for name, exists in obj.rels.items() if exists]  # type: ignore[attr-defined]


class RelationSerializer(serializers.Serializer[dict[str, Any]]):
    results = UserWithRelationSerializer(many=True)


class UserDeactivationSerializer(serializers.ModelSerializer[UserDeactivation]):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = UserDeactivation
        fields = ("user", "password", "for_deletion")
        extra_kwargs = {
            "for_deletion": {"write_only": True, "default": False},
        }

    def create(self, validated_data: dict[str, Any]) -> UserDeactivation:
        user, password, for_deletion = (
            cast("User", validated_data["user"]),
            validated_data["password"],
            validated_data["for_deletion"],
        )
        if not user.check_password(password):
            raise serializers.ValidationError(
                {"password": gettext("Your password was not correct.")}
            )
        return user.deactivate(for_deletion=for_deletion)
