from typing import Any

from django.urls import reverse

import pytest
from pytest_mock import MockerFixture

from asu.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_follow(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.follow:write")
    profile = UserFactory.create()
    response = client.post(
        reverse(
            "api:auth:user-follow",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200
    assert response.json() == {"status": "following"}
    assert UserFollow.objects.get(from_user=user, to_user=profile)


@pytest.mark.django_db
def test_user_follow_subsequent_ok(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    url = reverse(
        "api:auth:user-follow",
        kwargs={"pk": profile.pk},
    )
    r1 = user_client.post(url)
    r2 = user_client.post(url)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json() == {"status": "following"}
    assert UserFollow.objects.get(from_user=user, to_user=profile)


@pytest.mark.django_db
def test_user_unfollow(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.follow:write")
    profile = UserFactory.create()
    follow = UserFollow.objects.create(from_user=user, to_user=profile)
    response = client.post(
        reverse(
            "api:auth:user-unfollow",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    with pytest.raises(UserFollow.DoesNotExist):
        follow.refresh_from_db()


@pytest.mark.django_db
def test_user_unfollow_subsequent_ok(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    follow = UserFollow.objects.create(from_user=user, to_user=profile)
    url = reverse(
        "api:auth:user-unfollow",
        kwargs={"pk": profile.pk},
    )
    r1 = user_client.post(url)
    r2 = user_client.post(url)
    assert r1.status_code == r2.status_code == 204
    with pytest.raises(UserFollow.DoesNotExist):
        follow.refresh_from_db()


@pytest.mark.django_db
def test_user_unfollow_ok_if_no_previous_relation(user_client: OAuthClient) -> None:
    profile = UserFactory.create()
    response = user_client.post(
        reverse(
            "api:auth:user-unfollow",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_fail_if_blocked(
    user: User,
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    profile = UserFactory.create()
    UserBlock.objects.create(from_user=user, to_user=profile)
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_fail_if_self(
    user: User,
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_fail_if_blocked_by(
    user: User,
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    profile = UserFactory.create()
    UserBlock.objects.create(from_user=profile, to_user=user)
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_require_authentication(
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.post(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        )
    )
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_require_user_token(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.post(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        ),
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
@pytest.mark.parametrize(
    "scope",
    ("", "user.follow:read"),
)
def test_user_follow_endpoints_require_scope(
    user: User,
    client: OAuthClient,
    endpoint: str,
    scope: str,
) -> None:
    client.set_user(user, scope=scope)
    response = client.post(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        ),
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
def test_user_follow_endpoints_non_existing_user(
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-follow",
        "api:auth:user-unfollow",
    ),
)
@pytest.mark.parametrize(
    "attrs",
    (
        {"is_frozen": True},
        {"is_active": False},
    ),
)
def test_user_follow_endpoints_disabled_users(
    user_client: OAuthClient,
    endpoint: str,
    attrs: dict[str, Any],
) -> None:
    profile = UserFactory.create(**attrs)
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_follow_private_sends_follow_request(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create(is_private=True)
    response = user_client.post(
        reverse(
            "api:auth:user-follow",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200
    assert response.json() == {"status": "follow_request_sent"}
    with pytest.raises(UserFollow.DoesNotExist):
        UserFollow.objects.get(from_user=user, to_user=profile)
    follow = UserFollowRequest.objects.get(
        from_user=user,
        to_user=profile,
    )
    assert follow.status == UserFollowRequest.Status.PENDING


@pytest.mark.django_db
def test_user_follow_private_sends_follow_request_subsequent_ok(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create(is_private=True)
    url = reverse(
        "api:auth:user-follow",
        kwargs={"pk": profile.pk},
    )
    r1 = user_client.post(url)
    r2 = user_client.post(url)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json() == {"status": "follow_request_sent"}
    with pytest.raises(UserFollow.DoesNotExist):
        UserFollow.objects.get(from_user=user, to_user=profile)
    follow = UserFollowRequest.objects.get(
        from_user=user,
        to_user=profile,
    )
    assert follow.status == UserFollowRequest.Status.PENDING


@pytest.mark.django_db
def test_user_follow_private_already_following(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create(is_private=True)
    UserFollow.objects.create(from_user=user, to_user=profile)
    response = user_client.post(
        reverse(
            "api:auth:user-follow",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 200
    assert response.json() == {"status": "following"}


@pytest.mark.django_db
def test_user_follow_request_list(
    user: User,
    client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    client.set_user(user, scope="user.follow:read")
    profile = UserFactory.create()
    UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    response = client.get(
        reverse(
            "api:auth:follow-request-list",
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "next": None,
        "previous": None,
        "results": [
            {
                "id": mocker.ANY,
                "from_user": {
                    "id": mocker.ANY,
                    "display_name": profile.display_name,
                    "username": profile.username,
                    "profile_picture": None,
                    "is_private": False,
                    "description": "",
                },
            }
        ],
    }


def test_user_follow_request_list_requires_authentication(client: OAuthClient) -> None:
    response = client.get(reverse("api:auth:follow-request-list"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_follow_request_list_requires_user_client(app_client: OAuthClient) -> None:
    response = app_client.get(
        reverse(
            "api:auth:follow-request-list",
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("scope", ("", "user.follow:write"))
def test_user_follow_request_list_requires_scope(
    user: User,
    client: OAuthClient,
    scope: str,
) -> None:
    client.set_user(user, scope=scope)
    response = client.get(
        reverse(
            "api:auth:follow-request-list",
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_follow_request_accept(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.follow:write")
    profile = UserFactory.create(is_private=True)
    request = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    response = client.post(
        reverse(
            "api:auth:follow-request-accept",
            kwargs={"pk": request.pk},
        )
    )
    assert response.status_code == 204
    assert UserFollow.objects.get(from_user=profile, to_user=user)
    request.refresh_from_db()
    assert request.status == UserFollowRequest.Status.APPROVED


@pytest.mark.django_db
def test_user_follow_request_reject(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.follow:write")
    profile = UserFactory.create(is_private=True)
    request = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    response = client.post(
        reverse(
            "api:auth:follow-request-reject",
            kwargs={"pk": request.pk},
        )
    )
    assert response.status_code == 204
    request.refresh_from_db()
    assert request.status == UserFollowRequest.Status.REJECTED


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:follow-request-accept",
        "api:auth:follow-request-reject",
    ),
)
def test_user_follow_request_responds_only_to_pending(
    user: User,
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    profile = UserFactory.create(is_private=True)
    request = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.REJECTED,
    )
    response = user_client.post(
        reverse(
            endpoint,
            kwargs={"pk": request.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:follow-request-accept",
        "api:auth:follow-request-reject",
    ),
)
def test_user_follow_request_respond_requires_authentication(
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.get(reverse(endpoint, kwargs={"pk": 1}))
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:follow-request-accept",
        "api:auth:follow-request-reject",
    ),
)
def test_user_follow_request_respond_requires_user_client(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.get(reverse(endpoint, kwargs={"pk": 1}))
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:follow-request-accept",
        "api:auth:follow-request-reject",
    ),
)
@pytest.mark.parametrize("scope", ("", "user.follow:read"))
def test_user_follow_request_respond_requires_scope(
    client: OAuthClient,
    user: User,
    endpoint: str,
    scope: str,
) -> None:
    client.set_user(user, scope=scope)
    response = client.post(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_followers(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    profile, private, inactive, frozen = (
        UserFactory.create(display_name="user1"),
        UserFactory.create(display_name="user2", is_private=True),
        UserFactory.create(is_active=False),
        UserFactory.create(is_frozen=True),
    )
    UserFollow.objects.bulk_create(
        [
            UserFollow(
                from_user=from_user,
                to_user=user,
            )
            for from_user in (profile, private, inactive, frozen)
        ]
    )

    response = user_client.get(
        reverse(
            "api:auth:user-followers",
            kwargs={"pk": user.pk},
        )
    )
    assert response.json() == {
        "next": None,
        "previous": None,
        "results": [
            {
                "description": "",
                "display_name": "user2",
                "id": mocker.ANY,
                "is_private": True,
                "profile_picture": None,
                "username": mocker.ANY,
            },
            {
                "description": "",
                "display_name": "user1",
                "id": mocker.ANY,
                "is_private": False,
                "profile_picture": None,
                "username": mocker.ANY,
            },
        ],
    }


@pytest.mark.django_db
def test_user_following(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    profile, private, inactive, frozen = (
        UserFactory.create(display_name="user1"),
        UserFactory.create(display_name="user2", is_private=True),
        UserFactory.create(is_active=False),
        UserFactory.create(is_frozen=True),
    )
    UserFollow.objects.bulk_create(
        [
            UserFollow(
                from_user=user,
                to_user=to_user,
            )
            for to_user in (profile, private, inactive, frozen)
        ]
    )

    response = user_client.get(
        reverse(
            "api:auth:user-following",
            kwargs={"pk": user.pk},
        )
    )
    assert response.json() == {
        "next": None,
        "previous": None,
        "results": [
            {
                "description": "",
                "display_name": "user2",
                "id": mocker.ANY,
                "is_private": True,
                "profile_picture": None,
                "username": mocker.ANY,
            },
            {
                "description": "",
                "display_name": "user1",
                "id": mocker.ANY,
                "is_private": False,
                "profile_picture": None,
                "username": mocker.ANY,
            },
        ],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-followers",
        "api:auth:user-following",
    ),
)
def test_user_follower_endpoints_respect_privacy(
    user: User,
    user_client: OAuthClient,
    endpoint: str,
) -> None:
    profile = UserFactory.create(is_private=True)
    url = reverse(endpoint, kwargs={"pk": profile.pk})

    response = user_client.get(url)
    assert response.status_code == 403

    user.add_following(to_user=profile)
    response = user_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-following",
        "api:auth:user-followers",
    ),
)
def test_user_follower_endpoints_require_authentication(
    user: User,
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.get(
        reverse(
            endpoint,
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-following",
        "api:auth:user-followers",
    ),
)
def test_user_follower_endpoints_client_credentials(
    user: User,
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.get(
        reverse(
            endpoint,
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-following",
        "api:auth:user-followers",
    ),
)
def test_user_follower_endpoints_client_credentials_respects_privacy(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    user = UserFactory.create(is_private=True)
    response = app_client.get(
        reverse(
            endpoint,
            kwargs={"pk": user.pk},
        )
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-following",
        "api:auth:user-followers",
    ),
)
def test_user_follower_endpoints_user_not_found(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.get(
        reverse(
            endpoint,
            kwargs={"pk": 1},
        )
    )
    assert response.status_code == 404
