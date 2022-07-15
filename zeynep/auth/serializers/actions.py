import django.core.validators
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext

from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from zeynep.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from zeynep.auth.serializers.user import UserPublicReadSerializer
from zeynep.verification.models import PasswordResetVerification

RelatedUserField = UserPublicReadSerializer(
    read_only=True,
    fields=(
        "id",
        "display_name",
        "username",
        "description",
        "is_private",
        "url",
    ),
)


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
    class Meta:
        model = UserBlock
        fields = ("from_user", "to_user")
        extra_kwargs = {
            "from_user": {"write_only": True},
            "to_user": {"write_only": True},
        }

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
        from_user = validated_data["from_user"]
        to_user = validated_data["to_user"]

        # If users block each other in any
        # direction, following is not allowed.
        blocks = self.get_rels(UserBlock, **validated_data)
        if blocks.exists():
            raise PermissionDenied

        if to_user.is_private:
            from_user.send_follow_request(to_user=to_user)
        else:
            from_user.add_following(to_user=to_user)

        return validated_data


class FollowRequestSerializer(serializers.ModelSerializer):
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
        extra_kwargs = {"url": {"view_name": "follow-request-detail"}}

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if instance.is_approved:
            instance.bond()
        return instance


class UserFollowersSerializer(serializers.ModelSerializer):
    from_user = RelatedUserField

    class Meta:
        model = UserFollow
        fields = ("from_user",)

    def to_representation(self, instance):
        return super().to_representation(instance).pop("from_user")


class UserFollowingSerializer(serializers.ModelSerializer):
    to_user = RelatedUserField

    class Meta:
        model = UserFollow
        fields = ("to_user",)

    def to_representation(self, instance):
        return super().to_representation(instance).pop("to_user")


class UserBlockedSerializer(UserFollowingSerializer):
    class Meta:
        model = UserBlock
        fields = ("to_user",)


class TicketSerializer(serializers.Serializer):  # noqa
    scope = serializers.ChoiceField(choices=["websocket"])
    ticket = serializers.CharField(read_only=True)

    def create(self, validated_data):
        user = self.context["request"].user
        scope = validated_data["scope"]
        ticket = user.create_ticket(scope)

        if ticket is None:
            raise PermissionDenied

        validated_data["ticket"] = ticket
        return validated_data
