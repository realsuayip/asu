from django.core import mail
from django.urls import reverse

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks

from asu.verification.models import PasswordResetVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_password_reset_send(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-list"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    assert len(callbacks) == 1
    assert len(mail.outbox) == 1

    verification = PasswordResetVerification.objects.get()
    assert verification.email == "helen@example.com"
    assert verification.user == user
    assert (
        f"<div class='code'><strong>{verification.code}</strong></div>"
        in mail.outbox[0].body
    )
    assert verification.is_eligible is False
    assert verification.date_completed is None


@pytest.mark.django_db
def test_user_password_reset_send_email_normalization(
    first_party_app_client: OAuthClient,
) -> None:
    UserFactory.create(email="helen@example.com")
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-list"),
        data={"email": "helen@Example.com"},
    )
    assert response.status_code == 201
    assert response.json() == {"email": "helen@example.com"}

    verification = PasswordResetVerification.objects.only("email").get()
    assert verification.email == "helen@example.com"


@pytest.mark.django_db
def test_user_password_reset_send_invalid_email(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-list"),
            data={"email": "nonexisting@example.com"},
        )
    assert response.status_code == 201
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_user_password_reset_send_user_with_unusable_password(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-list"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    assert len(mail.outbox) == 0
    assert (
        "Password reset request is cancelled because user"
        " did not have usable password, user_id=%s" % user.pk in caplog.messages
    )


@pytest.mark.django_db
def test_user_password_reset_send_requires_authentication(
    client: OAuthClient,
) -> None:
    response = client.post(
        reverse("api:verification:password-reset-list"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_password_reset_send_requires_first_party_app_client(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:verification:password-reset-list"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 403
