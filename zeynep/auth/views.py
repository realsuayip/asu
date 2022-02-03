from django.db import transaction
from django.utils.translation import gettext

from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.exceptions import ValidationError

from zeynep.auth.models import User
from zeynep.verification.models import RegistrationVerification


class UserPublicReadSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "date_joined",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "gender",
            "birth_date",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserCreateSerializer(serializers.HyperlinkedModelSerializer):
    consent = serializers.CharField(write_only=True)

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
            raise ValidationError(
                gettext(
                    "This e-mail could not be verified."
                    " Please provide a validated e-mail address."
                )
            )

        user = super().create(validated_data)
        verification.user = user
        verification.save(update_fields=["user"])
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "username",
            "gender",
            "birth_date",
            "consent",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserPermissions(permissions.IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if view.action == "create":
            return True

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        has_base_permission = super().has_object_permission(request, view, obj)

        if view.action == "partial_update":
            # Only self-update allowed.
            return (request.user == obj) and has_base_permission

        return has_base_permission


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "username"
    http_method_names = ["get", "post", "patch", "head", "options"]
    permission_classes = [UserPermissions]

    def get_queryset(self):
        if self.action == "partial_update":
            return User.objects.active()
        return User.objects.visible()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return UserUpdateSerializer

        if self.action == "create":
            return UserCreateSerializer

        return UserPublicReadSerializer
