from django.http import HttpResponseRedirect
from django.urls import reverse

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from zeynep.auth.models import User, UserBlock
from zeynep.auth.serializers.actions import (
    BlockSerializer,
    PasswordResetSerializer,
)
from zeynep.auth.serializers.user import (
    UserCreateSerializer,
    UserPrivateReadSerializer,
    UserPublicReadSerializer,
    UserUpdateSerializer,
)
from zeynep.utils.views import ExtendedViewSet


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


class UserViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "create", "update")
    lookup_field = "username"
    http_method_names = ["get", "post", "patch", "head", "options"]
    permission_classes = [UserPermissions]

    def get_queryset(self):
        if self.action == "partial_update":
            return User.objects.active()
        return User.objects.public()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return UserUpdateSerializer

        if self.action == "create":
            return UserCreateSerializer

        return UserPublicReadSerializer

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=UserPrivateReadSerializer,
    )
    def me(self, request):
        if request.method == "PATCH":
            detail = reverse(
                "user-detail",
                kwargs={"username": self.request.user.username},
            )
            return HttpResponseRedirect(
                detail, status=status.HTTP_307_TEMPORARY_REDIRECT
            )

        serializer = UserPrivateReadSerializer(
            self.request.user, context=self.get_serializer_context()
        )
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        serializer_class=PasswordResetSerializer,
        url_path="password-reset",
    )
    def reset_password(self, request):
        return self.get_action_save_response(request, PasswordResetSerializer)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def block(self, request, username):
        serializer = BlockSerializer(
            data={"from_user": self.request.user.pk, "to_user": username},
            context=self.get_serializer_context(),
        )
        return self.get_action_save_response(
            request, serializer, status_code=204
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def unblock(self, request, username):
        UserBlock.objects.filter(
            from_user_id=request.user.id,
            to_user__username=username,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
