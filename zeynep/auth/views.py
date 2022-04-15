from django.db.models import Count

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from zeynep.auth.models import User
from zeynep.auth.serializers.actions import (
    BlockSerializer,
    FollowSerializer,
    PasswordResetSerializer,
)
from zeynep.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
    UserSerializer,
)
from zeynep.utils.views import ExtendedViewSet


class UserPermissions(permissions.IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if view.action == "create":
            return True

        return super().has_permission(request, view)


class UserViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "create")
    lookup_field = "username"
    permission_classes = [UserPermissions]

    def get_queryset(self):
        queryset = User.objects.active().annotate(
            following_count=Count("following", distinct=True),
            follower_count=Count("followed_by", distinct=True),
        )

        if self.request.user.is_authenticated:
            return queryset.exclude(blocked__in=[self.request.user])

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer

        if self.action == "me":
            return UserSerializer

        return UserPublicReadSerializer

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=UserSerializer,
    )
    def me(self, request):
        serializer_class, context = (
            self.get_serializer_class(),
            self.get_serializer_context(),
        )

        if request.method == "PATCH":
            serializer = serializer_class(
                self.request.user,
                context=context,
                data=self.request.data,
                partial=True,
            )
            return self.get_action_save_response(self.request, serializer)

        serializer = serializer_class(self.request.user, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        serializer_class=PasswordResetSerializer,
        url_path="password-reset",
    )
    def reset_password(self, request):
        return self.get_action_save_response(request, PasswordResetSerializer)

    def _save_through(self, serializer_class, username):
        # Common save method for user blocking and following.
        serializer = serializer_class(
            data={"from_user": self.request.user.pk, "to_user": username},
            context=self.get_serializer_context(),
        )
        return self.get_action_save_response(
            self.request, serializer, status_code=204
        )

    def _delete_through(self, serializer_class, username):
        # Common delete method for user blocking and following.
        model = serializer_class.Meta.model
        model.objects.filter(
            from_user_id=self.request.user.id,
            to_user__username=username,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def through_action(method):
        return action(
            detail=True,
            methods=["post"],
            permission_classes=[permissions.IsAuthenticated],
        )(method)

    @through_action
    def block(self, request, username):
        return self._save_through(BlockSerializer, username)

    @through_action
    def unblock(self, request, username):
        return self._delete_through(BlockSerializer, username)

    @through_action
    def follow(self, request, username):
        return self._save_through(FollowSerializer, username)

    @through_action
    def unfollow(self, request, username):
        return self._delete_through(FollowSerializer, username)
