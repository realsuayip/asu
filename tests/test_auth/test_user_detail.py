import datetime
import zoneinfo

from django.urls import reverse

import pytest
from pytest_django import DjangoAssertNumQueries
from pytest_mock import MockerFixture

from asu.auth.models import User, UserBlock
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_detail(
    user_client: OAuthClient,
    mocker: MockerFixture,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    profile = UserFactory.create(
        display_name="Helen",
        username="helen",
        email="helen@example.com",
        description="hello world!",
        website="https://example.com",
        birth_date=datetime.date(2000, 1, 1),
        created_at=datetime.datetime(2025, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC")),
    )

    with django_assert_num_queries(
        1  # fetch current user
        + 1  # fetch profile
        + 2  # fetch follower count + following count
    ):
        response = user_client.get(
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
        "is_private": False,
        "description": "hello world!",
        "website": "https://example.com",
        "following_count": 0,
        "follower_count": 0,
        "created_at": "2025-01-01T00:00:00Z",
    }


@pytest.mark.django_db
def test_user_detail_client_credentials(
    user: User,
    app_client: OAuthClient,
) -> None:
    response = app_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 200


def test_user_detail_requires_authentication(client: OAuthClient) -> None:
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
    user_client: OAuthClient,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    with django_assert_num_queries(
        1  # fetch current user
        + 2  # fetch follower count + following count
    ):
        response = user_client.get(
            reverse(
                "api:auth:user-detail",
                kwargs={"pk": user.pk},
            )
        )
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == str(user.pk)


@pytest.mark.django_db
def test_user_detail_follow_counts(
    user: User,
    app_client: OAuthClient,
) -> None:
    profile, user2 = UserFactory.create_batch(size=2)

    # 2 followers and 1 following
    user.add_following(to_user=profile)
    user2.add_following(to_user=profile)
    profile.add_following(to_user=user2)

    response = app_client.get(
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
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()

    UserBlock.objects.create(from_user=user, to_user=profile)
    response = user_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_detail_returns_ok_while_being_blocked(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()

    UserBlock.objects.create(from_user=profile, to_user=user)
    response = user_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_detail_frozen_user(app_client: OAuthClient) -> None:
    frozen_profile = UserFactory.create(is_frozen=True)
    response = app_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": frozen_profile.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_detail_inactive_user(app_client: OAuthClient) -> None:
    frozen_profile = UserFactory.create(is_active=False)
    response = app_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": frozen_profile.pk},
        )
    )
    assert response.status_code == 404
