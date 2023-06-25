from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from django.db.models import Count, Exists, OuterRef, QuerySet
from django.db.models.functions import JSONObject
from django.shortcuts import get_object_or_404

from rest_framework import parsers, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters

from asu.auth import schemas
from asu.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from asu.auth.permissions import (
    RequireFirstParty,
    RequireScope,
    RequireToken,
    RequireUser,
)
from asu.auth.serializers.actions import (
    BlockSerializer,
    FollowRequestSerializer,
    FollowSerializer,
    PasswordResetSerializer,
    ProfilePictureEditSerializer,
    RelationSerializer,
    TicketSerializer,
    UserBlockedSerializer,
    UserFollowersSerializer,
    UserFollowingSerializer,
)
from asu.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
    UserSerializer,
)
from asu.messaging.serializers import MessageComposeSerializer
from asu.utils.rest import IDFilter, get_paginator
from asu.utils.typing import UserRequest
from asu.utils.views import ExtendedViewSet

if TYPE_CHECKING:
    from rest_framework.decorators import ViewSetAction


F = TypeVar("F", bound=Callable[..., Any])


class RelationFilter(filters.FilterSet):
    ids = IDFilter(required=True)


class UserLookupFilter(filters.FilterSet):
    username = filters.CharFilter(required=True, lookup_expr="iexact")


class UserViewSet(ExtendedViewSet):
    mixins = ("list", "retrieve", "create")
    permission_classes = [RequireToken]
    # ^ Allow everyone for mixins listed above, for actions, each
    # have their permission classes set separately.
    serializer_classes = {
        "create": UserCreateSerializer,
        "me": UserSerializer,
        "by": UserPublicReadSerializer,
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
    filterset_classes = {"relations": RelationFilter, "by": UserLookupFilter}
    serializer_class = UserPublicReadSerializer
    schemas = schemas.user
    scopes = {
        "me": "user.profile",
        "block": "user.block",
        "unblock": "user.block",
        "follow": "user.follow",
        "unfollow": "user.follow",
        "relations": "user.profile",
    }

    def get_queryset(self) -> QuerySet[User]:
        queryset = User.objects.active()

        if self.request.user and self.request.user.is_authenticated:
            queryset = queryset.exclude(blocked__in=[self.request.user])

        if self.action in ["list", "retrieve", "by"]:
            return queryset.annotate(
                following_count=Count("following", distinct=True),
                follower_count=Count("followed_by", distinct=True),
            )

        return queryset

    def get_object(self) -> User:
        pk = self.kwargs["pk"]

        if self.request.user is not None:
            # Todo: 'retrieve' check might be removed once follower
            #  annotations above are removed.
            self_view = self.request.user.pk == pk
            if self_view and self.action != "retrieve":
                return self.request.user

        user: User = super().get_object()
        return user

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=UserSerializer,
    )
    def me(self, request: Request) -> Response:
        if request.method == "PATCH":
            serializer = self.get_serializer(
                self.request.user, data=self.request.data, partial=True
            )
            return self.get_action_save_response(self.request, serializer)

        serializer = self.get_serializer(self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[RequireToken],
        serializer_class=UserPublicReadSerializer,
        filter_backends=[filters.DjangoFilterBackend],
        url_name="lookup",
    )
    def by(self, request: Request) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        user = get_object_or_404(queryset)

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["patch"],
        permission_classes=[RequireToken],
        serializer_class=PasswordResetSerializer,
        url_path="password-reset",
    )
    def reset_password(self, request: Request) -> Response:
        return self.get_action_save_response(request)

    def save_through(self, pk: int) -> Response:
        # Common save method for user blocking and following.
        to_user = self.get_object()
        serializer = self.get_serializer(
            data={"from_user": self.request.user.pk, "to_user": to_user.pk}
        )
        return self.get_action_save_response(self.request, serializer, status_code=204)

    def delete_through(self, pk: int, model: type[UserFollow | UserBlock]) -> Response:
        # Common delete method for user blocking and following.
        to_user = self.get_object()
        model.objects.filter(from_user=self.request.user, to_user=to_user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def through_action(method: F) -> ViewSetAction[F]:
        return action(
            detail=True,
            methods=["post"],
            permission_classes=[RequireUser, RequireScope],
        )(method)

    @through_action
    def block(self, request: Request, pk: int) -> Response:
        return self.save_through(pk)

    @through_action
    def unblock(self, request: Request, pk: int) -> Response:
        return self.delete_through(pk, model=UserBlock)

    @through_action
    def follow(self, request: Request, pk: int) -> Response:
        return self.save_through(pk)

    @through_action
    def unfollow(self, request: Request, pk: int) -> Response:
        return self.delete_through(pk, model=UserFollow)

    def list_follow_through(
        self, queryset: QuerySet[UserFollow | UserBlock]
    ) -> Response:
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserFollowersSerializer,
        pagination_class=get_paginator("cursor", ordering="-date_created"),
        permission_classes=[RequireToken],
    )
    def followers(self, request: Request, pk: int) -> Response:
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
        permission_classes=[RequireToken],
    )
    def following(self, request: Request, pk: int) -> Response:
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
        permission_classes=[RequireUser, RequireScope],
        serializer_class=UserBlockedSerializer,
    )
    def blocked(self, request: UserRequest) -> Response:
        queryset = UserBlock.objects.filter(
            from_user=request.user,
            to_user__is_active=True,
            to_user__is_frozen=False,
        ).select_related("to_user")
        return self.list_follow_through(queryset)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireFirstParty],
        serializer_class=MessageComposeSerializer,
    )
    def message(self, request: Request, pk: int) -> Response:
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
        permission_classes=[RequireUser, RequireFirstParty],
        serializer_class=TicketSerializer,
    )
    def ticket(self, request: Request) -> Response:
        """
        Used to create an authentication ticket for the current user. A
        signed string will be returned, which can be used as an
        authentication token in case conventional methods are not
        possible e.g., through WebSocket protocol.
        """
        return self.get_action_save_response(
            request, status_code=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[RequireUser, RequireFirstParty],
        serializer_class=ProfilePictureEditSerializer,
        parser_classes=[parsers.MultiPartParser],
        url_path="profile-picture",
    )
    def profile_picture(self, request: Request) -> Response:
        if request.method == "DELETE":
            self.request.user.delete_profile_picture()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(self.request.user, data=request.data)
        return self.get_action_save_response(request, serializer)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=RelationSerializer,
        filter_backends=[filters.DjangoFilterBackend],
    )
    def relations(self, request: UserRequest) -> Response:
        user = request.user
        queryset = User.objects.active().only("id", "username", "display_name")
        queryset = queryset.annotate(
            rels=JSONObject(
                following=Exists(
                    UserFollow.objects.filter(
                        to_user=OuterRef("pk"),
                        from_user=user,
                    )
                ),
                followed_by=Exists(
                    UserFollow.objects.filter(
                        to_user=user,
                        from_user=OuterRef("pk"),
                    )
                ),
                blocking=Exists(
                    UserBlock.objects.filter(
                        to_user=OuterRef("pk"),
                        from_user=user,
                    )
                ),
                blocked_by=Exists(
                    UserBlock.objects.filter(
                        to_user=user,
                        from_user=OuterRef("pk"),
                    )
                ),
                follow_request_sent=Exists(
                    UserFollowRequest.objects.filter(
                        to_user=OuterRef("pk"),
                        from_user=user,
                        status=UserFollowRequest.Status.PENDING,
                    )
                ),
                follow_request_received=Exists(
                    UserFollowRequest.objects.filter(
                        to_user=user,
                        from_user=OuterRef("pk"),
                        status=UserFollowRequest.Status.PENDING,
                    )
                ),
            ),
        )
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer({"results": queryset})
        return Response(serializer.data)


class FollowRequestViewSet(ExtendedViewSet):
    mixins = ("list", "partial_update")
    permission_classes = [RequireUser, RequireScope]
    serializer_class = FollowRequestSerializer
    pagination_class = get_paginator("cursor", ordering="-date_created")
    schemas = schemas.follow_request
    scopes = {"list": "user.follow", "partial_update": "user.follow"}

    def get_queryset(self) -> QuerySet[UserFollowRequest]:
        return self.request.user.get_pending_follow_requests().select_related(
            "from_user"
        )
