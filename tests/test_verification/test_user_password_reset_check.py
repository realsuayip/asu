from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_mock import MockerFixture

from asu.verification.models import PasswordResetVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_password_reset_check(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        email="helen@example.com",
        user=user,
    )
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": verification.email,
        "consent": mocker.ANY,
    }
    verification.refresh_from_db()
    assert verification.is_eligible is True
    assert verification.verified_at is not None
    assert verification.completed_at is None


@pytest.mark.django_db
def test_user_password_reset_check_expires_code_after_use(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        email="helen@example.com",
        user=user,
    )
    url, payload = (
        reverse("api:verification:password-reset-check"),
        {
            "email": verification.email,
            "code": verification.code,
        },
    )
    r1 = first_party_app_client.post(url, data=payload)
    r2 = first_party_app_client.post(url, data=payload)
    assert r1.status_code == 200
    assert r2.status_code == 404


@pytest.mark.django_db
def test_user_password_reset_check_bad_code(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        email="helen@example.com",
        user=user,
    )
    verification.code = "123456"
    verification.save(update_fields=["code", "updated_at"])
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-check"),
        data={
            "email": verification.email,
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_password_reset_check_expired_code(
    first_party_app_client: OAuthClient,
) -> None:
    past = timezone.now() - timedelta(seconds=settings.PASSWORD_VERIFY_PERIOD + 10)
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        email="helen@example.com",
        user=user,
        created_at=past,
    )

    response = first_party_app_client.post(
        reverse("api:verification:password-reset-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 404
