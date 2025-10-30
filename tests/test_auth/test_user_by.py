import datetime

from django.urls import reverse

import pytest
from pytest_mock import MockerFixture

from asu.auth.models import User
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_by_requires_authentication(client: OAuthClient) -> None:
    response = client.get(
        reverse(
            "api:auth:user-lookup",
            query={"username": "hello"},
        )
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_by(
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    profile = UserFactory.create(
        display_name="Helen",
        username="helen",
        email="helen@example.com",
        description="hello world!",
        website="https://example.com",
        gender="unspecified",
        birth_date=datetime.date(2000, 1, 1),
        date_joined=datetime.date(2025, 1, 1),
    )
    response = user_client.get(
        reverse(
            "api:auth:user-lookup",
            query={
                "username": profile.username,
            },
        ),
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": mocker.ANY,
        "display_name": "Helen",
        "username": "helen",
        "profile_picture": None,
        "date_joined": "2025-01-01T00:00:00Z",
        "is_private": False,
        "description": "hello world!",
        "website": "https://example.com",
        "following_count": 0,
        "follower_count": 0,
        "url": mocker.ANY,
    }


@pytest.mark.django_db
def test_user_by_client_credentials(
    app_client: OAuthClient,
    user: User,
) -> None:
    response = app_client.get(
        reverse(
            "api:auth:user-lookup",
            query={"username": user.username},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_by_user_not_found(app_client: OAuthClient) -> None:
    response = app_client.get(
        reverse(
            "api:auth:user-lookup",
            query={"username": "helen"},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_by_query_param_required(app_client: OAuthClient) -> None:
    r1 = app_client.get(
        reverse(
            "api:auth:user-lookup",
            query={"username": ""},
        )
    )
    r2 = app_client.get(reverse("api:auth:user-lookup"))
    assert r1.status_code == 400
    assert r2.status_code == 400
    assert r1.json()["errors"] == {
        "username": [
            {
                "message": "This field is required.",
                "code": "required",
            }
        ]
    }
