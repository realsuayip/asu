import functools
from typing import Any, NoReturn, TypeVar, cast

import django.core.exceptions
from django.contrib.auth.password_validation import validate_password
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
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
from asu.verification.models import PasswordResetVerification

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
            {
                "email": gettext(
                    "This e-mail could not be verified. Please provide"
                    " a validated e-mail address."
                )
            }
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        email, password = validated_data["email"], validated_data["password"]
        try:
            user = User.objects.get(email=email)
            if not user.has_usable_password():
                # This block should be unreachable in normal circumstances since
                # this condition is also checked before sending code to email.
                # However, if the consent is generated somehow this check
                # ensures the password validation still fails.
                raise ValueError
        except (User.DoesNotExist, ValueError):
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
        user.revoke_other_tokens(self.context["request"].auth)

        send_notice = functools.partial(
            user.send_transactional_mail, message=messages.password_change_notice
        )
        transaction.on_commit(send_notice)
        return validated_data


class PasswordChangeSerializer(serializers.ModelSerializer[User]):
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("password", "new_password")
        extra_kwargs = {
            "password": {
                "max_length": None,
                "write_only": True,
                "style": {"input_type": "password"},
            },
        }

    @transaction.atomic
    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        request = self.context["request"]
        current, new = validated_data["password"], validated_data["new_password"]

        if not instance.check_password(current):
            raise serializers.ValidationError(
                {"password": gettext("Your password was not correct.")}
            )

        try:
            validate_password(new, user=instance)
        except django.core.exceptions.ValidationError as err:
            raise serializers.ValidationError({"new_password": err.messages})

        instance.set_password(new)
        instance.save(update_fields=["password", "date_modified"])
        instance.revoke_other_tokens(request.auth)

        send_notice = functools.partial(
            instance.send_transactional_mail, message=messages.password_change_notice
        )
        transaction.on_commit(send_notice)
        return instance


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
