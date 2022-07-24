from django.db.models import Count

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from zeynep.auth.models import User, UserBlock, UserFollow
from zeynep.auth.serializers.actions import (
    BlockSerializer,
    FollowRequestSerializer,
    FollowSerializer,
    PasswordResetSerializer,
    ProfilePictureEditSerializer,
    TicketSerializer,
    UserBlockedSerializer,
    UserFollowersSerializer,
    UserFollowingSerializer,
)
from zeynep.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
    UserSerializer,
)
from zeynep.messaging.serializers import MessageComposeSerializer
from zeynep.utils.rest import get_paginator
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
    serializer_classes = {
        "create": UserCreateSerializer,
        "me": UserSerializer,
        "block": BlockSerializer,
        "unblock": BlockSerializer,
        "follow": FollowSerializer,
        "unfollow": FollowSerializer,
        "followers": UserFollowersSerializer,
        "following": UserFollowingSerializer,
        "blocked": UserBlockedSerializer,
        "reset_password": PasswordResetSerializer,
        "message": MessageComposeSerializer,
        "ticket": TicketSerializer,
        "profile_picture": ProfilePictureEditSerializer,
    }
    serializer_class = UserPublicReadSerializer

    def get_queryset(self):
        queryset = User.objects.active()

        if self.request.user.is_authenticated:
            queryset = queryset.exclude(blocked__in=[self.request.user])

        if self.action in ["list", "retrieve"]:
            return queryset.annotate(
                following_count=Count("following", distinct=True),
                follower_count=Count("followed_by", distinct=True),
            )

        return queryset

    def get_object(self):
        self_view = self.request.user.username == self.kwargs.get("username")
        if self_view and self.action != "retrieve":
            return self.request.user
        return super().get_object()

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=UserSerializer,
    )
    def me(self, request):
        if request.method == "PATCH":
            serializer = self.get_serializer(
                self.request.user, data=self.request.data, partial=True
            )
            return self.get_action_save_response(self.request, serializer)

        serializer = self.get_serializer(self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["patch"],
        permission_classes=[permissions.AllowAny],
        serializer_class=PasswordResetSerializer,
        url_path="password-reset",
    )
    def reset_password(self, request):
        return self.get_action_save_response(request)

    def save_through(self, username):
        # Common save method for user blocking and following.
        to_user = self.get_object()
        serializer = self.get_serializer(
            data={"from_user": self.request.user.pk, "to_user": to_user.pk}
        )
        return self.get_action_save_response(
            self.request, serializer, status_code=204
        )

    def delete_through(self, username):
        # Common delete method for user blocking and following.
        to_user = self.get_object()
        model = self.get_serializer_class().Meta.model
        model.objects.filter(
            from_user=self.request.user,
            to_user=to_user,
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
        return self.save_through(username)

    @through_action
    def unblock(self, request, username):
        return self.delete_through(username)

    @through_action
    def follow(self, request, username):
        return self.save_through(username)

    @through_action
    def unfollow(self, request, username):
        return self.delete_through(username)

    def list_follow_through(self, queryset):
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserFollowersSerializer,
        pagination_class=get_paginator("cursor", ordering="-date_created"),
    )
    def followers(self, request, username):
        user = self.get_object()
        queryset = UserFollow.objects.filter(
            to_user=user,
            from_user__is_active=True,
            from_user__is_frozen=False,
        ).select_related("from_user")
        return self.list_follow_through(queryset)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserFollowingSerializer,
        pagination_class=get_paginator("cursor", ordering="-date_created"),
    )
    def following(self, request, username):
        user = self.get_object()
        queryset = UserFollow.objects.filter(
            from_user=user,
            to_user__is_active=True,
            to_user__is_frozen=False,
        ).select_related("to_user")
        return self.list_follow_through(queryset)

    @action(
        detail=False,
        methods=["get"],
        pagination_class=get_paginator("cursor", ordering="-date_created"),
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=UserBlockedSerializer,
    )
    def blocked(self, request):
        queryset = UserBlock.objects.filter(
            from_user=request.user,
            to_user__is_active=True,
            to_user__is_frozen=False,
        ).select_related("to_user")
        return self.list_follow_through(queryset)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=MessageComposeSerializer,
    )
    def message(self, request, username):
        context = self.get_serializer_context()
        context["recipient"] = self.get_object()
        serializer = self.get_serializer(data=request.data, context=context)
        return self.get_action_save_response(
            request,
            serializer,
            status_code=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        serializer_class=TicketSerializer,
    )
    def ticket(self, request):
        return self.get_action_save_response(
            request, status_code=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def profile_picture(self, request):
        if request.method == "DELETE":
            self.request.user.delete_profile_picture()
            return Response(status=204)

        serializer = self.get_serializer(self.request.user, data=request.data)
        return self.get_action_save_response(request, serializer)


class FollowRequestViewSet(ExtendedViewSet):
    mixins = ("list", "update")
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FollowRequestSerializer
    pagination_class = get_paginator("cursor", ordering="-date_created")

    def get_queryset(self):
        return self.request.user.get_pending_follow_requests().select_related(
            "from_user"
        )
