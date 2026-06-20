from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoAssertNumQueries

from asu.verification.models import PasswordResetVerification

from tests.conftest import OAuthClient
from tests.factories import PasswordResetVerificationFactory, UserFactory


@pytest.mark.django_db
def test_user_password_reset_verify(
    first_party_app_client: OAuthClient,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerificationFactory.create(
        email="helen@example.com",
        user=user,
        code="123456",
    )
    with django_assert_num_queries(
        1  # fetch token
        + 1  # fetch verification
        + 1  # update verification
    ):
        response = first_party_app_client.post(
            reverse("api:v1:verification:password-reset-verify"),
            data={
                "id": verification.pk,
                "code": "123456",
            },
        )
    assert response.status_code == 204
    verification.refresh_from_db()
    assert PasswordResetVerification.objects.eligible().only("id").get() == verification
    assert verification.verified_at is not None
    assert verification.completed_at is None


@pytest.mark.django_db
def test_user_password_reset_verify_expires_code_after_use(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerificationFactory.create(
        email="helen@example.com",
        user=user,
        code="123456",
    )
    url, payload = (
        reverse("api:v1:verification:password-reset-verify"),
        {
            "id": verification.pk,
            "code": "123456",
        },
    )
    r1 = first_party_app_client.post(url, data=payload)
    r2 = first_party_app_client.post(url, data=payload)
    assert r1.status_code == 204
    assert r2.status_code == 404


@pytest.mark.django_db
def test_user_password_reset_verify_bad_code(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerificationFactory.create(
        email="helen@example.com",
        user=user,
        code="123456",
    )
    response = first_party_app_client.post(
        reverse("api:v1:verification:password-reset-verify"),
        data={
            "id": verification.pk,
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_password_reset_verify_expired_code(
    first_party_app_client: OAuthClient,
) -> None:
    past = timezone.now() - timedelta(
        seconds=settings.PASSWORD_RESET_VERIFY_TIMEOUT + 10
    )
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerificationFactory.create(
        email="helen@example.com",
        user=user,
        created_at=past,
        code="123456",
    )

    response = first_party_app_client.post(
        reverse("api:v1:verification:password-reset-verify"),
        data={
            "id": verification.pk,
            "code": "123456",
        },
    )
    assert response.status_code == 404
