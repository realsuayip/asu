import re
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks

from asu.auth.models import Application
from asu.verification.models import EmailVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_email_change_check(client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    verification = EmailVerification.objects.create(
        email="helen_new@example.com",
        user=user,
    )
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"email": verification.email}
    verification.refresh_from_db()
    user.refresh_from_db()
    assert verification.verified_at is not None
    assert user.email == "helen_new@example.com"


@pytest.mark.django_db
def test_user_email_change_check_expires_code_after_use(client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    verification = EmailVerification.objects.create(
        email="helen_new@example.com",
        user=user,
    )
    url, payload = (
        reverse("api:verification:email-verification-check"),
        {
            "email": verification.email,
            "code": verification.code,
        },
    )
    r1 = client.post(url, data=payload)
    r2 = client.post(url, data=payload)
    assert r1.status_code == 200
    assert r2.status_code == 404


@pytest.mark.django_db
def test_user_email_change_check_bad_code(client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")
    verification = EmailVerification.objects.create(
        email="helen_new@example.com",
        user=user,
    )
    verification.code = "123456"
    verification.save(update_fields=["code", "updated_at"])
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": verification.email,
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_email_change_check_expired_code(client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")

    past = timezone.now() - timedelta(seconds=settings.EMAIL_VERIFY_PERIOD + 10)
    verification = EmailVerification.objects.create(
        email="helen_new@example.com",
        user=user,
        created_at=past,
    )

    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email",
    (
        "helen_new@example.com",
        "helen_other@example.com",
    ),
)
def test_user_email_change_nullifies_other_verifications(
    client: OAuthClient,
    email: str,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")

    v1, v2 = EmailVerification.objects.bulk_create(
        [
            EmailVerification(
                email="helen_new@example.com",
                user=user,
                code="111111",
            ),
            EmailVerification(
                email=email,
                user=user,
                code="111112",
            ),
        ]
    )
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={"email": v1.email, "code": v1.code},
    )
    assert response.status_code == 200

    v1.refresh_from_db()
    v2.refresh_from_db()

    assert v1.verified_at is not None
    assert v2.nulled_by == v1


@pytest.mark.django_db
def test_user_email_change_flow(
    client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="")

    # Step 1: Send verification email containing code
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("api:verification:email-verification-list"),
            data={"email": "helen_new@example.com"},
        )
    assert response.status_code == 201
    code = re.search(
        r"<div class='code'><strong>(\d+)</strong></div>",
        mail.outbox[0].body,
    ).group(1)

    # Step 2: Use grabbed code change the email
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": "helen_new@example.com",
            "code": code,
        },
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "helen_new@example.com"


@pytest.mark.django_db
def test_user_email_change_check_requires_authentication(client: OAuthClient) -> None:
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_email_change_change_requires_first_party_app_client(
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    client.set_user(user, scope="", app=authorization_code_third_party_app)
    response = client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": "helen_new@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_email_check_send_requires_user(
    first_party_app_client: OAuthClient,
) -> None:
    response = first_party_app_client.post(
        reverse("api:verification:email-verification-check"),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 403
