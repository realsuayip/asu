import functools
from typing import TYPE_CHECKING, Any

from drf_spectacular.contrib.django_oauth_toolkit import DjangoOAuthToolkitScheme
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.auth.permissions import OAuthPermission
from asu.auth.serializers.actions import ManyRelatedUserField, PasswordResetSerializer
from asu.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
    UserSerializer,
)
from asu.messaging.serializers import MessageComposeSerializer
from asu.utils.rest import APIError, EmptySerializer

if TYPE_CHECKING:
    from drf_spectacular.openapi import AutoSchema


__all__ = ["user", "follow_request"]


class OAuthScheme(DjangoOAuthToolkitScheme):  # type: ignore[no-untyped-call]
    priority = 1

    def get_security_requirement(
        self, auto_schema: "AutoSchema"
    ) -> dict[str, list[Any]] | list[dict[str, list[Any]]]:
        view = auto_schema.view
        permissions = view.get_permissions()

        has_oauth = any(isinstance(p, OAuthPermission) for p in permissions)
        if not has_oauth:
            return []

        try:
            scopes = view.required_scopes
        except KeyError:
            scopes = []
        return {"oauth2": scopes}


not_found_example = OpenApiExample(
    "user was not found",
    value={"detail": "Not found."},
    response_only=True,
    status_codes=["404"],
)

action = functools.partial(
    extend_schema,
    request=EmptySerializer,
    examples=[not_found_example],
    responses={204: None, 404: APIError},
)

block = action(summary="Block a user")
unblock = action(summary="Unblock a user")

follow = action(
    summary="Follow a user",
    description="Depending on the user's choice, this action"
    " will either send a follow request (if the account is private)"
    " or immediately follow the user. Request might fail with 403 if"
    " the user is not allowed to follow the other user (i.e., in case of"
    " blocking relations).",
    examples=[
        not_found_example,
        OpenApiExample(
            "following is not allowed",
            value={"detail": "You do not have permission to perform this action."},
            response_only=True,
            status_codes=["403"],
        ),
    ],
    responses={204: None, 404: APIError, 403: APIError},
)
unfollow = action(summary="Unfollow a user")


create = extend_schema(
    summary="Register a new user",
    description="Before you send a request to this endpoint,"
    " you need to acquire 'consent' string. This string is obtained via "
    "email validation through registration verification flow. Check"
    " registration verification documentation to learn more.",
    examples=[
        OpenApiExample(
            "bad user information",
            value={
                "email": ["Enter a valid email address."],
                "display_name": ["This field may not be blank."],
                "username": [
                    "Usernames can only contain latin letters,"
                    "numerals and underscores. Trailing, leading"
                    " or consecutive underscores are not allowed."
                ],
            },
            response_only=True,
            status_codes=["400"],
        ),
        OpenApiExample(
            "bad consent",
            value={
                "email": [
                    "This e-mail could not be verified. Please provide a"
                    " validated e-mail address."
                ]
            },
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={201: UserCreateSerializer, 400: OpenApiTypes.OBJECT},
)

retrieve = extend_schema(
    summary="Retrieve a user",
    examples=[not_found_example],
    responses={200: UserPublicReadSerializer, 404: APIError},
)

user_resp = {200: ManyRelatedUserField, 403: APIError, 404: APIError}
followers = extend_schema(summary="List followers of a user", responses=user_resp)
following = extend_schema(summary="List follows of a user", responses=user_resp)
blocked = extend_schema(summary="List blocked users", responses=user_resp)

message = extend_schema(
    summary="Send a message to user",
    responses={
        200: MessageComposeSerializer,
        403: APIError,
        404: APIError,
    },
)

get_me = extend_schema(
    summary="Retrieve authenticated user",
    responses={200: UserSerializer},
    methods=["get"],
)
patch_me = extend_schema(
    summary="Update authenticated user",
    responses={200: UserSerializer, 400: OpenApiTypes.OBJECT},
    methods=["patch"],
    examples=[
        OpenApiExample(
            "bad values",
            value={
                "username": ["This field may not be blank."],
                "gender": ['"potato" is not a valid choice.'],
                "birth_date": [
                    "Date has wrong format. Use one of these"
                    " formats instead: YYYY-MM-DD."
                ],
                "website": ["Enter a valid URL."],
            },
            response_only=True,
            status_codes=["400"],
        )
    ],
)
me = lambda f: get_me(patch_me(f))  # noqa: E731

reset_password = extend_schema(
    summary="Reset password",
    responses={
        200: PasswordResetSerializer,
        400: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "bad values",
            value={
                "email": ["This e-mail could not be verified."],
                "password": [
                    "This password is too common.",
                    "This password is too short. It must contain at"
                    " least 8 characters.",
                ],
            },
            response_only=True,
            status_codes=["400"],
        )
    ],
)

put_profile_picture = extend_schema(
    summary="Upload new profile picture",
    methods=["put"],
)
delete_profile_picture = extend_schema(
    summary="Remove profile picture",
    methods=["delete"],
)
profile_picture = lambda f: put_profile_picture(delete_profile_picture(f))  # noqa: E731

ticket = extend_schema("Create authentication ticket")

user = {
    "create": create,
    "retrieve": retrieve,
    "block": block,
    "unblock": unblock,
    "follow": follow,
    "unfollow": unfollow,
    "me": me,
    "reset_password": reset_password,
    "followers": followers,
    "following": following,
    "blocked": blocked,
    "message": message,
    "profile_picture": profile_picture,
    "ticket": ticket,
}

list_follow_requests = extend_schema(summary="List follow requests")
update_follow_request = extend_schema(summary="Respond to a follow request")

follow_request = {
    "list": list_follow_requests,
    "partial_update": update_follow_request,
}
