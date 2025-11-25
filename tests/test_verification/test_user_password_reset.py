import re
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks
from pytest_mock import MockerFixture

from asu.verification.models import PasswordResetVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_password_reset(first_party_app_client: OAuthClient) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "password": "hln_j1070",
    }
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data=payload,
    )
    assert response.status_code == 200
    assert response.json() == {"email": "helen@example.com"}

    user.refresh_from_db()
    assert user.check_password("hln_j1070")

    verification.refresh_from_db()
    assert verification.date_completed is not None


@pytest.mark.django_db
def test_user_password_reset_case_invalid_consent(
    first_party_app_client: OAuthClient,
) -> None:
    payload = {
        "email": "helen@example.com",
        "consent": "bad:consent",
        "password": "Hln_1900",
    }
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": [
            {
                "code": "invalid",
                "message": "This e-mail could not be verified."
                " Please provide a validated e-mail address.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_password_reset_case_expired_consent(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    mocker.patch(
        "django.utils.timezone.now",
        return_value=timezone.now()
        + timedelta(seconds=settings.PASSWORD_RESET_PERIOD + 1),
    )
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": [
            {
                "code": "invalid",
                "message": "This e-mail could not be verified."
                " Please provide a validated e-mail address.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_password_reset_case_unusable_password(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": [
            {
                "code": "invalid",
                "message": "This e-mail could not be verified."
                " Please provide a validated e-mail address.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_password_reset_password_validation(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "password": "helenexample",
    }
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "password": [
            {
                "message": "The password is too similar to the e-mail.",
                "code": "invalid",
            }
        ]
    }


def test_user_password_reset_requires_authentication(client: OAuthClient) -> None:
    response = client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": "bad:consent",
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_password_reset_requires_requires_first_party_app(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": "bad:consent",
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_password_reset_nullifies_other_verifications(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    v1, v2 = PasswordResetVerification.objects.bulk_create(
        [
            PasswordResetVerification(
                email="helen@example.com",
                user=user,
                date_verified=timezone.now(),
                code="111111",
            ),
            PasswordResetVerification(
                email="helen@example.com",
                user=user,
                date_verified=timezone.now(),
                code="111112",
            ),
        ]
    )
    consent = v1.create_consent()
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 200

    v1.refresh_from_db()
    v2.refresh_from_db()

    assert v1.date_completed is not None
    assert v2.nulled_by == v1


@pytest.mark.django_db
def test_user_password_reset_flow(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user = UserFactory.create(email="helen@example.com")

    # Step 1: Send verification email containing code
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-list"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    code = re.search(
        r"<div class='code'><strong>(\d+)</strong></div>",
        mail.outbox[0].body,
    ).group(1)

    # Step 2: Use grabbed code to get a consent
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-check"),
        data={
            "email": "helen@example.com",
            "code": code,
        },
    )
    assert response.status_code == 200
    consent = response.json()["consent"]

    # Step 3: Reset password with given consent
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-reset"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.check_password("Hln_1900")
