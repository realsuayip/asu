import datetime
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoAssertNumQueries
from pytest_mock import MockerFixture

from asu.auth.models import AccessToken, Application, User, UserBlock
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_detail(
    user: User,
    oauth_client: OAuthClient,
    mocker: MockerFixture,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    oauth_client.set_user(user)
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

    with django_assert_num_queries(
        1  # fetch current user
        + 1  # fetch profile
        + 2  # fetch follower count + following count
    ):
        response = oauth_client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": profile.pk},
            )
        )
    assert response.status_code == 200
    detail = response.json()
    assert detail == {
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
def test_user_detail_client_credentials(
    oauth_client: OAuthClient,
    user: User,
    client_credentials_app: Application,
) -> None:
    access = AccessToken.objects.create(
        scope="",
        expires=timezone.now() + timedelta(minutes=15),
        token="some-client-token",
        application=client_credentials_app,
    )
    oauth_client.set_token(access.token)

    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 200


def test_user_detail_requires_authentication() -> None:
    client = OAuthClient()
    response = client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": 1},
        )
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_detail_self(
    user: User,
    oauth_client: OAuthClient,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    oauth_client.set_user(user)
    with django_assert_num_queries(
        1  # fetch current user
        + 2  # fetch follower count + following count
    ):
        response = oauth_client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": user.pk},
            )
        )
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == user.pk


@pytest.mark.django_db
def test_user_detail_follow_counts(
    user: User,
    oauth_client: OAuthClient,
) -> None:
    oauth_client.set_user(user)
    profile, user2 = UserFactory.create_batch(size=2)

    # 2 followers and 1 following
    user.add_following(to_user=profile)
    user2.add_following(to_user=profile)
    profile.add_following(to_user=user2)

    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["following_count"] == 1
    assert detail["follower_count"] == 2


@pytest.mark.django_db
def test_user_detail_returns_ok_while_blocking(
    user: User,
    oauth_client: OAuthClient,
) -> None:
    oauth_client.set_user(user)
    profile = UserFactory.create()

    UserBlock.objects.create(from_user=user, to_user=profile)
    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_detail_returns_ok_while_being_blocked(
    user: User,
    oauth_client: OAuthClient,
) -> None:
    oauth_client.set_user(user)
    profile = UserFactory.create()

    UserBlock.objects.create(from_user=profile, to_user=user)
    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_detail_frozen_user(
    user: User,
    oauth_client: OAuthClient,
) -> None:
    oauth_client.set_user(user)
    frozen_profile = UserFactory.create(is_frozen=True)
    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": frozen_profile.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_detail_inactive_user(
    user: User,
    oauth_client: OAuthClient,
) -> None:
    oauth_client.set_user(user)
    frozen_profile = UserFactory.create(is_active=False)
    response = oauth_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": frozen_profile.pk},
        )
    )
    assert response.status_code == 404
