from django.urls import reverse

import pytest
from pytest_mock import MockerFixture

from asu.auth.models import User, UserBlock, UserFollow, UserFollowRequest
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_relations_unrelated(
    user: User,
    client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    client.set_user(user, scope="user.profile:read")
    UserFactory.create(username="helen")
    UserFactory.create(username="bob")
    response = client.get(
        reverse(
            "api:auth:user-relations",
            query={
                "usernames": "helen,bob",
            },
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"id": mocker.ANY, "relations": [], "username": "bob"},
            {"id": mocker.ANY, "relations": [], "username": "helen"},
        ]
    }


def test_user_relations_requires_authentication(client: OAuthClient) -> None:
    response = client.get(reverse("api:auth:user-relations"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_relations_requires_user_token(app_client: OAuthClient) -> None:
    response = app_client.get(reverse("api:auth:user-relations"))
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("scope", ("", "user.profile:write"))
def test_user_relations_requires_scope(
    user: User,
    client: OAuthClient,
    scope: str,
) -> None:
    client.set_user(user, scope=scope)
    response = client.get(reverse("api:auth:user-relations"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_relations_related_mixed(
    user: User,
    client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    client.set_user(user, scope="user.profile:read")
    helen, bob, james = (
        UserFactory.create(username="helen"),
        UserFactory.create(username="bob"),
        UserFactory.create(username="james"),
    )
    UserFollow.objects.create(from_user=user, to_user=helen)
    UserFollowRequest.objects.create(
        from_user=bob,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    UserBlock.objects.create(from_user=james, to_user=user)
    response = client.get(
        reverse(
            "api:auth:user-relations",
            query={
                "usernames": "helen,bob,james",
            },
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["blocked_by"],
                "username": "james",
            },
            {
                "id": mocker.ANY,
                "relations": ["follow_request_received"],
                "username": "bob",
            },
            {
                "id": mocker.ANY,
                "relations": ["following"],
                "username": "helen",
            },
        ]
    }


@pytest.mark.django_db
def test_user_relations_following(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollow.objects.create(from_user=user, to_user=helen)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["following"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_followed_by(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollow.objects.create(from_user=helen, to_user=user)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["followed_by"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_both_following_and_followed_by(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollow.objects.create(from_user=helen, to_user=user)
    UserFollow.objects.create(from_user=user, to_user=helen)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["following", "followed_by"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_blocking(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserBlock.objects.create(from_user=user, to_user=helen)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["blocking"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_blocked_by(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserBlock.objects.create(from_user=helen, to_user=user)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["blocked_by"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_both_blocking_and_blocked_by(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserBlock.objects.create(from_user=helen, to_user=user)
    UserBlock.objects.create(from_user=user, to_user=helen)

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["blocking", "blocked_by"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_follow_request_sent(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollowRequest.objects.create(
        from_user=user,
        to_user=helen,
        status=UserFollowRequest.Status.PENDING,
    )

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["follow_request_sent"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_follow_request_received(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollowRequest.objects.create(
        from_user=helen,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["follow_request_received"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_both_follow_request_sent_and_received(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollowRequest.objects.create(
        from_user=helen,
        to_user=user,
        status=UserFollowRequest.Status.PENDING,
    )
    UserFollowRequest.objects.create(
        from_user=user,
        to_user=helen,
        status=UserFollowRequest.Status.PENDING,
    )

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["follow_request_sent", "follow_request_received"],
                "username": "helen",
            }
        ]
    }


@pytest.mark.django_db
def test_user_relations_mixed_followed_by_follow_request_sent(
    user: User,
    user_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    helen = UserFactory.create(username="helen")
    UserFollow.objects.create(from_user=helen, to_user=user)
    UserFollowRequest.objects.create(
        from_user=user,
        to_user=helen,
        status=UserFollowRequest.Status.PENDING,
    )

    response = user_client.get(
        reverse(
            "api:auth:user-relations",
            query={"usernames": "helen"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": mocker.ANY,
                "relations": ["followed_by", "follow_request_sent"],
                "username": "helen",
            }
        ]
    }
