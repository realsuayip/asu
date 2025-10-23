import datetime
from datetime import timedelta
from typing import Any
from unittest.mock import ANY

from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoAssertNumQueries
from pytest_mock import MockerFixture

from asu.auth.models import AccessToken, Application, User
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_me(
    oauth_client: OAuthClient,
    mocker: MockerFixture,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    user = UserFactory.create(
        display_name="Helen",
        username="helen",
        email="helen@example.com",
        description="hello world!",
        website="https://example.com",
        gender="unspecified",
        birth_date=datetime.date(2000, 1, 1),
        date_joined=datetime.date(2025, 1, 1),
    )
    oauth_client.set_user(user)
    with django_assert_num_queries(
        1  # fetch user
        + 2  # fetch otp devices (totp, static)
    ):
        response = oauth_client.get(reverse("api:auth:user-me"))
    assert response.status_code == 200
    assert response.json() == {
        "id": mocker.ANY,
        "display_name": "Helen",
        "username": "helen",
        "email": "helen@example.com",
        "description": "hello world!",
        "website": "https://example.com",
        "profile_picture": None,
        "gender": "unspecified",
        "language": "en",
        "birth_date": "2000-01-01",
        "date_joined": "2025-01-01T00:00:00Z",
        "is_private": False,
        "allows_receipts": True,
        "allows_all_messages": True,
        "two_factor_enabled": False,
        "url": mocker.ANY,
    }


def test_user_me_requires_authentication() -> None:
    client = OAuthClient()
    response = client.get(reverse("api:auth:user-me"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_me_requires_user_authentication(
    oauth_client: OAuthClient,
    client_credentials_app: Application,
) -> None:
    access = AccessToken.objects.create(
        scope="",
        expires=timezone.now() + timedelta(minutes=15),
        token="some-client-token",
        application=client_credentials_app,
    )
    oauth_client.set_token(access.token)

    response = oauth_client.get(reverse("api:auth:user-me"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_me_update(user: User, oauth_client: OAuthClient) -> None:
    oauth_client.set_user(user)

    response = oauth_client.patch(
        reverse("api:auth:user-me"),
        data={
            "display_name": "__Potato__",
            "description": "Lorem ipsum",
        },
    )
    detail = response.json()
    assert detail["display_name"] == "__Potato__"
    assert detail["description"] == "Lorem ipsum"

    user.refresh_from_db()
    assert user.display_name == "__Potato__"
    assert user.description == "Lorem ipsum"


@pytest.mark.django_db
def test_user_me_update_username_taken(user: User, oauth_client: OAuthClient) -> None:
    UserFactory.create(username="suzie")

    oauth_client.set_user(user)
    response = oauth_client.patch(
        reverse("api:auth:user-me"),
        data={"username": "Suzie"},
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "username": [
            {
                "code": "invalid",
                "message": "The username you specified is already in use.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_me_update_disallow_email(user: User, oauth_client: OAuthClient) -> None:
    oauth_client.set_user(user)

    email = "hello@example.com"
    response = oauth_client.patch(reverse("api:auth:user-me"), data={"email": email})
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.email != email


@pytest.mark.django_db
@pytest.mark.parametrize(
    "scope, detail",
    (
        (
            "user.profile:read",
            {
                "id": ANY,
                "display_name": "Helen",
                "username": "helen",
                "description": "hello world!",
                "website": "https://example.com",
                "profile_picture": None,
                "date_joined": "2025-01-01T00:00:00Z",
                "is_private": False,
                "url": ANY,
            },
        ),
        (
            "user.profile:read user.profile.private:read",
            {
                "id": ANY,
                "display_name": "Helen",
                "username": "helen",
                "description": "hello world!",
                "website": "https://example.com",
                "profile_picture": None,
                "date_joined": "2025-01-01T00:00:00Z",
                "is_private": False,
                "birth_date": "2000-01-01",
                "allows_receipts": True,
                "allows_all_messages": True,
                "gender": "unspecified",
                "language": "en",
                "two_factor_enabled": False,
                "url": ANY,
            },
        ),
        (
            "user.profile:read user.profile.email:read",
            {
                "id": ANY,
                "display_name": "Helen",
                "username": "helen",
                "email": "helen@example.com",
                "description": "hello world!",
                "website": "https://example.com",
                "profile_picture": None,
                "date_joined": "2025-01-01T00:00:00Z",
                "is_private": False,
                "url": ANY,
            },
        ),
        (
            "user.profile:read user.profile.private:read user.profile.email:read",
            {
                "id": ANY,
                "display_name": "Helen",
                "username": "helen",
                "email": "helen@example.com",
                "description": "hello world!",
                "website": "https://example.com",
                "profile_picture": None,
                "date_joined": "2025-01-01T00:00:00Z",
                "is_private": False,
                "birth_date": "2000-01-01",
                "allows_receipts": True,
                "allows_all_messages": True,
                "gender": "unspecified",
                "language": "en",
                "two_factor_enabled": False,
                "url": ANY,
            },
        ),
    ),
)
def test_user_me_third_party_token(
    oauth_client: OAuthClient,
    authorization_code_third_party_app: Application,
    scope: str,
    detail: dict[str, Any],
) -> None:
    user = UserFactory.create(
        display_name="Helen",
        username="helen",
        email="helen@example.com",
        description="hello world!",
        website="https://example.com",
        date_joined=datetime.date(2025, 1, 1),
        birth_date=datetime.date(2000, 1, 1),
    )
    access = AccessToken.objects.create(
        user=user,
        scope=scope,
        expires=timezone.now() + timedelta(minutes=15),
        token="third-party-token",
        application=authorization_code_third_party_app,
    )
    oauth_client.set_token(access.token)
    response = oauth_client.get(reverse("api:auth:user-me"))
    assert response.status_code == 200
    assert response.json() == detail


@pytest.mark.django_db
@pytest.mark.parametrize(
    "scope",
    (
        "",
        "user.profile.email:read",
        "user.profile.private:read",
        "user.profile.email:read user.profile.private:read",
    ),
)
def test_user_me_third_party_token_case_bad_scope(
    user: User,
    oauth_client: OAuthClient,
    authorization_code_third_party_app: Application,
    scope: str,
) -> None:
    access = AccessToken.objects.create(
        user=user,
        scope=scope,
        expires=timezone.now() + timedelta(minutes=15),
        token="third-party-token",
        application=authorization_code_third_party_app,
    )
    oauth_client.set_token(access.token)
    response = oauth_client.get(reverse("api:auth:user-me"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_me_third_party_token_update_not_allowed(
    user: User,
    oauth_client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    access = AccessToken.objects.create(
        user=user,
        scope="user:profile:read"
        " user.profile:write"
        " user.profile.email:read"
        " user.profile.private:read",
        expires=timezone.now() + timedelta(minutes=15),
        token="third-party-token",
        application=authorization_code_third_party_app,
    )
    oauth_client.set_token(access.token)
    response = oauth_client.patch(
        reverse("api:auth:user-me"),
        data={"display_name": "Helen"},
    )
    assert response.status_code == 403
