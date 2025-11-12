from typing import Any

from django.urls import reverse

import pytest
from pytest_mock import MockerFixture

from asu.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_block(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.block:write")
    profile = UserFactory.create()
    response = client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)


@pytest.mark.django_db
def test_user_block_subsequent_ok(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    url = reverse(
        "api:auth:user-block",
        kwargs={"pk": profile.pk},
    )
    r1 = user_client.post(url)
    r2 = user_client.post(url)
    assert r1.status_code == r2.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)


@pytest.mark.django_db
def test_user_unblock(
    user: User,
    client: OAuthClient,
) -> None:
    client.set_user(user, scope="user.block:write")
    profile = UserFactory.create()
    block = UserBlock.objects.create(from_user=user, to_user=profile)
    response = client.post(
        reverse(
            "api:auth:user-unblock",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    with pytest.raises(UserBlock.DoesNotExist):
        block.refresh_from_db()


@pytest.mark.django_db
def test_user_unblock_subsequent_ok(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    block = UserBlock.objects.create(from_user=user, to_user=profile)
    url = reverse(
        "api:auth:user-unblock",
        kwargs={"pk": profile.pk},
    )
    r1 = user_client.post(url)
    r2 = user_client.post(url)
    assert r1.status_code == r2.status_code == 204
    with pytest.raises(UserBlock.DoesNotExist):
        block.refresh_from_db()


@pytest.mark.django_db
def test_user_unblock_ok_if_no_previous_relation(user_client: OAuthClient) -> None:
    profile = UserFactory.create()
    response = user_client.post(
        reverse(
            "api:auth:user-unblock",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
def test_user_block_endpoints_fail_if_self(
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
def test_user_block_allowed_while_being_blocked(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    UserBlock.objects.create(from_user=profile, to_user=user)

    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)


@pytest.mark.django_db
def test_user_unblock_allowed_while_being_blocked(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    block, _ = UserBlock.objects.bulk_create(
        (
            UserBlock(from_user=user, to_user=profile),
            UserBlock(from_user=profile, to_user=user),
        )
    )
    response = user_client.post(
        reverse(
            "api:auth:user-unblock",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    with pytest.raises(UserBlock.DoesNotExist):
        block.refresh_from_db()


@pytest.mark.parametrize(
    "endpoint",
    (
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
def test_user_block_endpoints_require_authentication(
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
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
def test_user_block_endpoints_require_user_token(
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
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
@pytest.mark.parametrize(
    "scope",
    ("", "user.block:read"),
)
def test_user_block_endpoints_require_scope(
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
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
def test_user_block_endpoints_non_existing_user(
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
        "api:auth:user-block",
        "api:auth:user-unblock",
    ),
)
@pytest.mark.parametrize(
    "attrs",
    (
        {"is_frozen": True},
        {"is_active": False},
    ),
)
def test_user_block_endpoints_disabled_users(
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
def test_user_block_removes_follow(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    follow = UserFollow.objects.create(from_user=user, to_user=profile)
    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)
    with pytest.raises(UserFollow.DoesNotExist):
        follow.refresh_from_db()


@pytest.mark.django_db
def test_user_block_removes_follower(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    follower = UserFollow.objects.create(from_user=profile, to_user=user)
    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)
    with pytest.raises(UserFollow.DoesNotExist):
        follower.refresh_from_db()


@pytest.mark.django_db
def test_user_block_rejects_received_pending_follow_request(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    request_received = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)
    request_received.refresh_from_db()
    assert request_received.status == UserFollowRequest.Status.REJECTED


@pytest.mark.django_db
def test_user_block_rejects_sent_pending_follow_request(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    request_sent = UserFollowRequest.objects.create(
        from_user=user,
        to_user=profile,
        status=UserFollowRequest.Status.PENDING,
    )
    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)
    request_sent.refresh_from_db()
    assert request_sent.status == UserFollowRequest.Status.REJECTED


@pytest.mark.django_db
def test_user_block_only_rejects_pending_follow_requests(
    user: User,
    user_client: OAuthClient,
) -> None:
    profile = UserFactory.create()
    request_previously_accepted = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.APPROVED,
    )
    request_received = UserFollowRequest.objects.create(
        from_user=profile,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    response = user_client.post(
        reverse(
            "api:auth:user-block",
            kwargs={"pk": profile.pk},
        )
    )
    assert response.status_code == 204
    assert UserBlock.objects.get(from_user=user, to_user=profile)
    request_received.refresh_from_db()
    request_previously_accepted.refresh_from_db()
    assert request_received.status == UserFollowRequest.Status.REJECTED
    assert request_previously_accepted.status == UserFollowRequest.Status.APPROVED


@pytest.mark.django_db
def test_user_blocked_list(
    user: User,
    client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    client.set_user(user, scope="user.block:read")
    profile, private, inactive, frozen = (
        UserFactory.create(display_name="user1"),
        UserFactory.create(display_name="user2", is_private=True),
        UserFactory.create(is_active=False),
        UserFactory.create(is_frozen=True),
    )
    UserBlock.objects.bulk_create(
        [
            UserBlock(
                from_user=user,
                to_user=to_user,
            )
            for to_user in (profile, private, inactive, frozen)
        ]
    )
    response = client.get(reverse("api:auth:user-blocked"))
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


def test_user_blocked_list_requires_authentication(client: OAuthClient) -> None:
    response = client.get(reverse("api:auth:user-blocked"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_blocked_list_requires_user_token(app_client: OAuthClient) -> None:
    response = app_client.get(reverse("api:auth:user-blocked"))
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("scope", ("", "user.block:write"))
def test_user_blocked_list_requires_scope(
    user: User,
    client: OAuthClient,
    scope: str,
) -> None:
    client.set_user(user, scope=scope)
    response = client.get(reverse("api:auth:user-blocked"))
    assert response.status_code == 403
