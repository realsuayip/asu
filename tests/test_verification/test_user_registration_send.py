from django.core import mail
from django.urls import reverse

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks

from asu.verification.models import RegistrationVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_verification_registration_send(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = first_party_app_client.post(
            reverse("api:verification:registration-send"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    assert len(callbacks) == 1
    assert len(mail.outbox) == 1

    verification = RegistrationVerification.objects.get()
    assert response.json() == {
        "id": str(verification.pk),
        "email": "helen@example.com",
    }
    assert verification.email == "helen@example.com"
    assert (
        f"<div class='code'><strong>{verification.code}</strong></div>"
        in mail.outbox[0].body
    )
    assert verification.user is None
    assert verification.is_eligible is False
    assert verification.completed_at is None


@pytest.mark.django_db
def test_verification_registration_send_email_normalization(
    first_party_app_client: OAuthClient,
) -> None:
    response = first_party_app_client.post(
        reverse("api:verification:registration-send"),
        data={"email": "helen@Example.com"},
    )
    assert response.status_code == 201
    verification = RegistrationVerification.objects.only("id", "email").get()
    assert response.json() == {
        "id": str(verification.pk),
        "email": "helen@example.com",
    }
    assert verification.email == "helen@example.com"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "wanted_email, existing_email",
    (
        ("helen@example.com", "helen@example.com"),
        ("HELEN@example.com", "helen@example.com"),
    ),
)
def test_verification_registration_send_email_taken(
    first_party_app_client: OAuthClient,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
    wanted_email: str,
    existing_email: str,
) -> None:
    UserFactory.create(email=existing_email)
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:registration-send"),
            data={"email": wanted_email},
        )
    assert "Registration mail cancelled, email=%s" % wanted_email in caplog.messages
    assert response.status_code == 201
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_verification_registration_send_requires_authentication(
    client: OAuthClient,
) -> None:
    response = client.post(
        reverse("api:verification:registration-send"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_verification_registration_send_requires_first_party_app_client(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:verification:registration-send"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 403
