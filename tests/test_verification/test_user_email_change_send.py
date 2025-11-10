from django.core import mail
from django.urls import reverse

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks

from asu.auth.models import Application
from asu.verification.models import EmailVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_email_change_send(
    client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = client.post(
            reverse("api:verification:email-verification-list"),
            data={"email": "helen_new@example.com"},
        )
    assert response.status_code == 201
    assert len(callbacks) == 1
    assert len(mail.outbox) == 1

    verification = EmailVerification.objects.get()
    assert verification.email == "helen_new@example.com"
    assert verification.user == user
    assert (
        f"<div class='code'><strong>{verification.code}</strong></div>"
        in mail.outbox[0].body
    )
    assert verification.date_verified is None


@pytest.mark.django_db
def test_user_email_change_send_email_normalization(client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    response = client.post(
        reverse("api:verification:email-verification-list"),
        data={"email": "helen_new@Example.com"},
    )
    assert response.status_code == 201
    assert response.json() == {"email": "helen_new@example.com"}

    verification = EmailVerification.objects.only("email").get()
    assert verification.email == "helen_new@example.com"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email",
    (
        "previously_existing@example.com",
        "PREVIOUSLY_EXISTING@example.com",
    ),
)
def test_user_email_change_send_email_taken(
    client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
    email: str,
) -> None:
    UserFactory.create(email=email)
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("api:verification:email-verification-list"),
            data={"email": "previously_existing@example.com"},
        )
    assert response.status_code == 201
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_user_email_change_send_requires_authentication(client: OAuthClient) -> None:
    response = client.post(
        reverse("api:verification:email-verification-list"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_email_change_send_requires_first_party_app_client(
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="", app=authorization_code_third_party_app)
    response = client.post(
        reverse("api:verification:email-verification-list"),
        data={"email": "helen_new@example.com"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_email_change_send_requires_user(
    first_party_app_client: OAuthClient,
) -> None:
    response = first_party_app_client.post(
        reverse("api:verification:email-verification-list"),
        data={"email": "helen@example.com"},
    )
    assert response.status_code == 403
