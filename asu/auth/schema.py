import functools

from rest_framework import serializers

from drf_spectacular.utils import OpenApiExample, OpenApiTypes, extend_schema

from asu.auth.serializers.user import (
    UserCreateSerializer,
    UserPublicReadSerializer,
)
from asu.utils.rest import APIError

not_found_example = OpenApiExample(
    "user was not found",
    value={"detail": "Not found."},
    response_only=True,
    status_codes=["404"],
)

action = functools.partial(
    extend_schema,
    request=serializers.Serializer,
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
            value={
                "detail": "You do not have permission"
                " to perform this action."
            },
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
