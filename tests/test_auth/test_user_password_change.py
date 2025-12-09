from django.core import mail
from django.urls import reverse

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks

from asu.auth.models import Application, RefreshToken, User
from tests.conftest import OAuthClient


@pytest.mark.django_db
def test_user_password_change(
    user: User,
    user_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user.set_password("0ld_password*")
    user.save(update_fields=["password", "updated_at"])
    token_to_be_revoked = user.issue_token()["refresh_token"]
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = user_client.post(
            reverse("api:auth:user-change-password"),
            data={
                "old_password": "0ld_password*",
                "new_password": "1new_password*",
            },
        )
    assert response.status_code == 204
    assert len(callbacks) == 1
    assert len(mail.outbox) == 1
    assert "Your password has been changed" in mail.outbox[0].body

    user.refresh_from_db()
    assert user.check_password("1new_password*")

    refresh = RefreshToken.objects.get(token=token_to_be_revoked)
    assert refresh.revoked is not None


@pytest.mark.django_db
def test_user_password_change_case_bad_current_password(
    user_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = user_client.post(
            reverse("api:auth:user-change-password"),
            data={
                "old_password": "0ld_password*",
                "new_password": "1new_password*",
            },
        )
    assert len(callbacks) == 0
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "old_password": [
            {
                "message": "Your password was not correct.",
                "code": "invalid",
            }
        ]
    }


@pytest.mark.django_db
def test_user_password_change_case_bad_new_password(
    user: User,
    user_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user.set_password("0ld_password*")
    user.save(update_fields=["password", "updated_at"])
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = user_client.post(
            reverse("api:auth:user-change-password"),
            data={
                "old_password": "0ld_password*",
                "new_password": "password",
            },
        )
    assert len(callbacks) == 0
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "new_password": [
            {
                "message": "This password is too common.",
                "code": "invalid",
            }
        ]
    }


def test_user_password_change_requires_authentication(client: OAuthClient) -> None:
    response = client.post(
        reverse("api:auth:user-change-password"),
        data={
            "password": "0ld_password*",
            "new_password": "password",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_password_change_requires_first_party_app_client(
    user: User,
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    client.set_user(user, app=authorization_code_third_party_app)
    response = client.post(
        reverse("api:auth:user-change-password"),
        data={
            "password": "0ld_password*",
            "new_password": "password",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_password_change_requires_user(
    first_party_app_client: OAuthClient,
) -> None:
    response = first_party_app_client.post(
        reverse("api:auth:user-change-password"),
        data={
            "password": "0ld_password*",
            "new_password": "password",
        },
    )
    assert response.status_code == 403
