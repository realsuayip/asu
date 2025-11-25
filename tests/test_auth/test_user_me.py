import datetime
import zoneinfo
from typing import Any
from unittest.mock import ANY

from django.urls import reverse

import pytest
from pytest_django import DjangoAssertNumQueries
from pytest_mock import MockerFixture

from asu.auth.models import Application, User
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_me(
    client: OAuthClient,
    mocker: MockerFixture,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    user = UserFactory.create(
        display_name="Helen",
        username="helen",
        email="helen@example.com",
        description="hello world!",
        website="https://example.com",
        birth_date=datetime.date(2000, 1, 1),
        created_at=datetime.datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")),
    )
    client.set_user(user)
    with django_assert_num_queries(
        1  # fetch user
        + 2  # fetch otp devices (totp, static)
    ):
        response = client.get(reverse("api:auth:user-me"))
    assert response.status_code == 200
    assert response.json() == {
        "id": mocker.ANY,
        "display_name": "Helen",
        "username": "helen",
        "email": "helen@example.com",
        "description": "hello world!",
        "website": "https://example.com",
        "profile_picture": None,
        "language": "en",
        "birth_date": "2000-01-01",
        "is_private": False,
        "allows_receipts": True,
        "allows_all_messages": True,
        "two_factor_enabled": False,
        "created_at": "2025-01-01T00:00:00Z",
    }


def test_user_me_requires_authentication() -> None:
    client = OAuthClient()
    response = client.get(reverse("api:auth:user-me"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_me_requires_user_authentication(app_client: OAuthClient) -> None:
    response = app_client.get(reverse("api:auth:user-me"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_me_update(
    user: User,
    user_client: OAuthClient,
) -> None:
    response = user_client.patch(
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
def test_user_me_update_username_taken(user_client: OAuthClient) -> None:
    UserFactory.create(username="suzie")

    response = user_client.patch(
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
def test_user_me_update_disallow_email(
    user: User,
    user_client: OAuthClient,
) -> None:
    email = "hello@example.com"
    response = user_client.patch(reverse("api:auth:user-me"), data={"email": email})
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
                "is_private": False,
                "created_at": "2025-01-01T00:00:00Z",
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
                "is_private": False,
                "birth_date": "2000-01-01",
                "allows_receipts": True,
                "allows_all_messages": True,
                "language": "en",
                "two_factor_enabled": False,
                "created_at": "2025-01-01T00:00:00Z",
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
                "is_private": False,
                "created_at": "2025-01-01T00:00:00Z",
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
                "is_private": False,
                "birth_date": "2000-01-01",
                "allows_receipts": True,
                "allows_all_messages": True,
                "language": "en",
                "two_factor_enabled": False,
                "created_at": "2025-01-01T00:00:00Z",
            },
        ),
    ),
)
def test_user_me_third_party_token(
    client: OAuthClient,
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
        birth_date=datetime.date(2000, 1, 1),
        created_at=datetime.datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")),
    )
    client.set_user(
        user,
        scope=scope,
        app=authorization_code_third_party_app,
    )
    response = client.get(reverse("api:auth:user-me"))
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
    client: OAuthClient,
    authorization_code_third_party_app: Application,
    scope: str,
) -> None:
    client.set_user(
        user,
        scope=scope,
        app=authorization_code_third_party_app,
    )
    response = client.get(reverse("api:auth:user-me"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_me_third_party_token_update_not_allowed(
    user: User,
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    client.set_user(
        user,
        scope="user:profile:read"
        " user.profile:write"
        " user.profile.email:read"
        " user.profile.private:read",
        app=authorization_code_third_party_app,
    )
    response = client.patch(
        reverse("api:auth:user-me"),
        data={"display_name": "Helen"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_me_properly_responds_with_405_rather_than_403(
    user: User,
    client: OAuthClient,
    authorization_code_third_party_app: Application,
):
    client.set_user(user, app=authorization_code_third_party_app)
    response = client.post(reverse("api:auth:user-me"))
    assert response.status_code == 405
