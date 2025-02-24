import functools
from typing import TYPE_CHECKING, Any

from drf_spectacular.contrib.django_oauth_toolkit import DjangoOAuthToolkitScheme
from drf_spectacular.utils import OpenApiExample, extend_schema

from asu.auth.permissions import OAuthPermission
from asu.auth.serializers.actions import (
    FollowSerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    RelationSerializer,
    UserConnectionSerializer,
)
from asu.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
    UserSerializer,
)
from asu.core.utils.openapi import Tag, examples, get_error_repr
from asu.core.utils.rest import APIError
from asu.messaging.serializers import MessageComposeSerializer

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


action = functools.partial(
    extend_schema,
    examples=[examples.not_found],
    responses={204: None, 404: APIError},
)

block = action(summary="Block a user", tags=[Tag.USER_BLOCK_OPERATIONS])
unblock = action(summary="Unblock a user", tags=[Tag.USER_BLOCK_OPERATIONS])

follow = action(
    summary="Follow a user",
    tags=[Tag.USER_FOLLOW_OPERATIONS],
    description="Depending on the user's choice, this action"
    " will either send a follow request (if the account is private)"
    " or immediately follow the user. Request might fail with 403 if"
    " the user is not allowed to follow the other user (i.e., in case of"
    " blocking relations).",
    examples=[examples.not_found, examples.permission_denied],
    responses={200: FollowSerializer, 404: APIError, 403: APIError},
)
unfollow = action(summary="Unfollow a user", tags=[Tag.USER_FOLLOW_OPERATIONS])


create = extend_schema(
    summary="Register a new user",
    tags=[Tag.USER_REGISTRATION],
    description="Before you send a request to this endpoint,"
    " you need to acquire 'consent' string. This string is obtained via "
    "email validation through registration verification flow. Check"
    " registration verification documentation to learn more.",
    examples=[
        OpenApiExample(
            "bad user information",
            value=get_error_repr(
                {
                    "email": ["Enter a valid email address."],
                    "display_name": ["This field may not be blank."],
                    "username": [
                        "Usernames can only contain latin letters,"
                        "numerals and underscores. Trailing, leading"
                        " or consecutive underscores are not allowed."
                    ],
                }
            ),
            response_only=True,
            status_codes=["400"],
        ),
        OpenApiExample(
            "bad consent",
            value=get_error_repr(
                {
                    "email": [
                        "This e-mail could not be verified. Please provide a"
                        " validated e-mail address."
                    ]
                }
            ),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    responses={201: UserCreateSerializer, 400: APIError},
)

retrieve = extend_schema(
    summary="Retrieve a user",
    tags=[Tag.USER_RETRIEVAL],
    examples=[examples.not_found],
    responses={200: UserPublicReadSerializer, 404: APIError},
)

followers = extend_schema(
    summary="List followers of a user",
    tags=[Tag.USER_FOLLOW_OPERATIONS],
    responses={200: UserConnectionSerializer(many=True), 404: APIError},
    examples=[examples.not_found],
)
following = extend_schema(
    summary="List follows of a user",
    tags=[Tag.USER_FOLLOW_OPERATIONS],
    responses={200: UserConnectionSerializer(many=True), 404: APIError},
    examples=[examples.not_found],
)
blocked = extend_schema(
    summary="List blocked users",
    tags=[Tag.USER_BLOCK_OPERATIONS],
    responses={200: UserConnectionSerializer(many=True)},
)

message = extend_schema(
    summary="Send a message to user",
    tags=[Tag.MESSAGING],
    responses={
        200: MessageComposeSerializer,
        403: APIError,
        404: APIError,
    },
    examples=[examples.not_found, examples.permission_denied],
)

get_me = extend_schema(
    summary="Retrieve authenticated user",
    tags=[Tag.USER_SETTINGS, Tag.USER_RETRIEVAL],
    responses={200: UserSerializer},
    methods=["get"],
)
patch_me = extend_schema(
    summary="Update authenticated user",
    tags=[Tag.USER_SETTINGS],
    responses={200: UserSerializer, 400: APIError},
    methods=["patch"],
    examples=[
        OpenApiExample(
            "bad values",
            value=get_error_repr(
                {
                    "username": ["This field may not be blank."],
                    "gender": ['"potato" is not a valid choice.'],
                    "birth_date": [
                        "Date has wrong format. Use one of these"
                        " formats instead: YYYY-MM-DD."
                    ],
                    "website": ["Enter a valid URL."],
                }
            ),
            response_only=True,
            status_codes=["400"],
        )
    ],
)
me = lambda f: get_me(patch_me(f))  # noqa: E731

by = extend_schema(
    summary="Retrieve a user by username",
    tags=[Tag.USER_RETRIEVAL],
    responses={200: UserPublicReadSerializer, 404: APIError},
    examples=[examples.not_found],
    filters=True,
)

reset_password = extend_schema(
    summary="Reset password",
    tags=[Tag.USER_PASSWORD_RESET],
    responses={
        200: PasswordResetSerializer,
        400: APIError,
    },
    examples=[
        OpenApiExample(
            "bad values",
            value=get_error_repr(
                {
                    "email": ["This e-mail could not be verified."],
                    "password": [
                        "This password is too common.",
                        "This password is too short. It must contain at"
                        " least 8 characters.",
                    ],
                }
            ),
            response_only=True,
            status_codes=["400"],
        )
    ],
)
change_password = extend_schema(
    summary="Change password",
    tags=[Tag.USER_SETTINGS],
    responses={204: PasswordChangeSerializer, 400: APIError},
)


put_profile_picture = extend_schema(
    summary="Upload new profile picture",
    tags=[Tag.USER_SETTINGS],
    methods=["put"],
)
delete_profile_picture = extend_schema(
    summary="Remove profile picture",
    tags=[Tag.USER_SETTINGS],
    methods=["delete"],
)
profile_picture = lambda f: put_profile_picture(delete_profile_picture(f))  # noqa: E731

ticket = extend_schema(
    summary="Create authentication ticket", tags=[Tag.USER_AUTHENTICATION]
)

relations = extend_schema(
    summary="List relations with given users",
    tags=[Tag.USER_FOLLOW_OPERATIONS, Tag.USER_BLOCK_OPERATIONS],
    responses={
        200: RelationSerializer,
        400: APIError,
    },
    examples=[
        OpenApiExample(
            "ids not provided",
            value=get_error_repr({"ids": ["This field is required."]}),
            response_only=True,
            status_codes=["400"],
        ),
        OpenApiExample(
            "too many ids",
            value=get_error_repr(
                {"ids": ["List contains 51 items, it should contain no more than 50."]}
            ),
            response_only=True,
            status_codes=["400"],
        ),
    ],
    filters=True,
)

deactivate = extend_schema(
    summary="Deactivate authenticated user",
    tags=[Tag.USER_SETTINGS],
    responses={204: None, 400: APIError},
    examples=[
        OpenApiExample(
            "bad password",
            value=get_error_repr({"password": ["Your password was not correct."]}),
            response_only=True,
            status_codes=["400"],
        )
    ],
)


user = {
    "create": create,
    "retrieve": retrieve,
    "block": block,
    "unblock": unblock,
    "follow": follow,
    "unfollow": unfollow,
    "me": me,
    "by": by,
    "reset_password": reset_password,
    "change_password": change_password,
    "followers": followers,
    "following": following,
    "blocked": blocked,
    "message": message,
    "profile_picture": profile_picture,
    "ticket": ticket,
    "relations": relations,
    "deactivate": deactivate,
}

list_follow_requests = extend_schema(
    summary="List follow requests", tags=[Tag.USER_FOLLOW_OPERATIONS]
)
update_follow_request = extend_schema(
    summary="Respond to a follow request", tags=[Tag.USER_FOLLOW_OPERATIONS]
)

follow_request = {
    "list": list_follow_requests,
    "partial_update": update_follow_request,
}
