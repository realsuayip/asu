import itertools
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.db.models.functions import JSONObject
from django.shortcuts import get_object_or_404

from rest_framework import mixins, parsers, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from rest_filters import Filter, FilterSet
from rest_filters.fields import CSVField

from asu.auth import schemas
from asu.auth.models import AccessToken, User, UserBlock, UserFollow, UserFollowRequest
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
    PasswordChangeSerializer,
    ProfilePictureEditSerializer,
    RelationSerializer,
    UnblockSerializer,
    UnfollowSerializer,
    UserConnectionSerializer,
    UserDeactivationSerializer,
)
from asu.auth.serializers.user import (
    UserPublicReadSerializer,
    UserSerializer,
)
from asu.core.utils.rest import EmptySerializer, get_paginator
from asu.core.utils.typing import UserRequest
from asu.core.utils.views import ExtendedViewSet


class RelationFilter(FilterSet[User]):
    usernames = Filter(
        CSVField(
            child=serializers.CharField(max_length=16),
            min_length=1,
            max_length=50,
        ),
        field="username",
        lookup="in",
        required=True,
    )


class UserLookupFilter(FilterSet[User]):
    username = Filter(
        serializers.CharField(max_length=16),
        field="username",
        lookup="iexact",
        required=True,
    )


class UserViewSet(mixins.RetrieveModelMixin, ExtendedViewSet[User]):
    sensitive_actions = {"followers", "following"}
    """
    These actions may reveal sensitive information about the user. If the user
    marked their account private, these will be inaccessible to users that
    do not follow the user. This check is enforced in `get_object()` method.
    """
    serializer_classes = {
        "me": UserSerializer,
        "by": UserPublicReadSerializer,
        "followers": UserConnectionSerializer,
        "following": UserConnectionSerializer,
        "blocked": UserConnectionSerializer,
        "profile_picture": ProfilePictureEditSerializer,
    }
    filterset_classes = {"relations": RelationFilter, "by": UserLookupFilter}
    serializer_class = UserPublicReadSerializer
    schemas = schemas.user
    scopes = {
        "me": "user.profile",
        "block": "user.block",
        "unblock": "user.block",
        "blocked": "user.block",
        "follow": "user.follow",
        "unfollow": "user.follow",
        "relations": "user.profile",
    }

    def get_permissions(self) -> Sequence[BasePermission]:
        # todo: use ExtendedViewSet?
        permission_classes = self.permission_classes
        if self.action == "retrieve":
            permission_classes = [RequireToken]
        return [permission() for permission in permission_classes]

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.active()

    def get_object(self) -> User:
        as_user = bool(self.request.user and self.request.user.is_authenticated)
        if as_user and (self.request.user.pk == self.kwargs["pk"]):
            # If the user is displaying their own object, don't
            # bother making additional database queries.
            return self.request.user
        user = super().get_object()
        if (
            as_user
            and self.action not in {"retrieve", "block", "unblock"}
            and self.request.user.has_block_rel(user)
        ):
            # If displayed user has blocking relations with the authenticated
            # user, make sure actions with `detail=True` are not available. For
            # example, people cannot follow or message users if they have been
            # blocked (or if they block).

            # Exceptions are made for 'retrieving', 'blocking' and 'unblocking'
            # actions. In that, people can block or unblock the person that
            # blocks them. To do that, they should be able to visit user detail
            # page, so retrieving is also allowed.
            raise PermissionDenied
        if (
            self.action in self.sensitive_actions
            and user.is_private
            and not (as_user and self.request.user.is_following(user))
        ):
            # If displayed user account is private, make sure sensitive actions
            # are only available to their followers.
            raise PermissionDenied
        return user

    def get_profile_attrs(self, token: AccessToken | None) -> dict[str, Any]:
        if not token:
            # Probably using browsable API or used `force_login` in tests
            # so, allow all fields. In production environment, token will
            # always be present.
            return {}
        granted_scopes = token.scope.split()
        fields = itertools.chain.from_iterable(
            fields
            for scope, fields in settings.OAUTH2_USER_FIELDS.items()
            if scope in granted_scopes
        )
        return {"fields": fields, "ref_name": "User"}

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=UserSerializer,
    )
    def me(self, request: UserRequest) -> Response:
        user, token = request.user, request.auth
        if request.method == "PATCH":
            if not RequireFirstParty().has_permission(request, self):
                # Only first-party applications might update the
                # user information.
                raise PermissionDenied
            serializer = self.get_serializer(user, data=request.data, partial=True)
            return self.perform_action(serializer)

        serializer = self.get_serializer(user, **self.get_profile_attrs(token))
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[RequireToken],
        serializer_class=UserPublicReadSerializer,
        url_name="lookup",
    )
    def by(self, request: Request) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        user = get_object_or_404(queryset)

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[RequireUser, RequireFirstParty],
        serializer_class=PasswordChangeSerializer,
        url_path="password-change",
    )
    def change_password(self, request: UserRequest) -> Response:
        return self.perform_action()

    def perform_relation_action(self) -> Response:
        # Common save method for user blocking and following.
        to_user = self.get_object()
        context = self.get_serializer_context()
        context["to_user"] = to_user
        serializer = self.get_serializer(data=self.request.data, context=context)
        return self.perform_action(serializer)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=BlockSerializer,
    )
    def block(self, request: Request, pk: UUID) -> Response:
        return self.perform_relation_action()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=UnblockSerializer,
    )
    def unblock(self, request: Request, pk: UUID) -> Response:
        return self.perform_relation_action()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=FollowSerializer,
    )
    def follow(self, request: Request, pk: UUID) -> Response:
        return self.perform_relation_action()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=UnfollowSerializer,
    )
    def unfollow(self, request: Request, pk: UUID) -> Response:
        return self.perform_relation_action()

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserConnectionSerializer,
        pagination_class=get_paginator("cursor", ordering="-from_userfollows"),
        permission_classes=[RequireToken],
    )
    def followers(self, request: Request, pk: UUID) -> Response:
        user = self.get_object()
        queryset = User.objects.active().filter(following=user)
        return self.perform_list_action(queryset)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=UserConnectionSerializer,
        pagination_class=get_paginator("cursor", ordering="-to_userfollows"),
        permission_classes=[RequireToken],
    )
    def following(self, request: Request, pk: UUID) -> Response:
        user = self.get_object()
        queryset = User.objects.active().filter(followed_by=user)
        return self.perform_list_action(queryset)

    @action(
        detail=False,
        methods=["get"],
        serializer_class=UserConnectionSerializer,
        pagination_class=get_paginator("cursor", ordering="-to_userblocks"),
        permission_classes=[RequireUser, RequireScope],
    )
    def blocked(self, request: UserRequest) -> Response:
        queryset = User.objects.active().filter(blocked_by=request.user)
        return self.perform_list_action(queryset)

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
        return self.perform_action(serializer)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=RelationSerializer,
    )
    def relations(self, request: UserRequest) -> Response:
        user = request.user
        queryset = User.objects.active().only("id", "username").order_by("-id")
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
        queryset = self.filter_queryset(queryset)[:50]
        serializer = self.get_serializer({"results": queryset})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[RequireUser, RequireFirstParty],
        serializer_class=UserDeactivationSerializer,
    )
    def deactivate(self, request: UserRequest) -> Response:
        return self.perform_action(status_code=status.HTTP_204_NO_CONTENT)


class FollowRequestViewSet(
    mixins.ListModelMixin,
    ExtendedViewSet[UserFollowRequest],
):
    permission_classes = [RequireUser, RequireScope]
    queryset = UserFollowRequest.objects.none()
    serializer_class = FollowRequestSerializer
    pagination_class = get_paginator("cursor", ordering="-id")
    schemas = schemas.follow_request
    scopes = {
        "list": "user.follow",
        "accept": "user.follow",
        "reject": "user.follow",
    }

    def get_queryset(self) -> QuerySet[UserFollowRequest]:
        queryset = self.request.user.get_pending_follow_requests()
        if self.action in ("accept", "reject"):
            return queryset.select_for_update()
        return queryset.select_related("from_user")

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=EmptySerializer,
    )
    def accept(self, request: UserRequest, pk: UUID) -> Response:
        with transaction.atomic():
            instance = self.get_object()
            instance.accept()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[RequireUser, RequireScope],
        serializer_class=EmptySerializer,
    )
    def reject(self, request: UserRequest, pk: UUID) -> Response:
        with transaction.atomic():
            instance = self.get_object()
            instance.reject()
        return Response(status=status.HTTP_204_NO_CONTENT)
