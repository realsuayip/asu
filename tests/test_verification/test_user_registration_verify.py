from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoAssertNumQueries

from asu.verification.models import RegistrationVerification

from tests.conftest import OAuthClient
from tests.factories import RegistrationVerificationFactory


@pytest.mark.django_db
def test_verification_registration_verify_a85(
    first_party_app_client: OAuthClient,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    verification = RegistrationVerificationFactory.create(code="123456")
    with django_assert_num_queries(
        1  # fetch token
        + 1  # fetch verification
        + 1  # update verification
    ):
        response = first_party_app_client.post(
            reverse("api:v1:verification:registration-verify"),
            data={
                "id": verification.pk,
                "code": "123456",
            },
        )
    assert response.status_code == 204
    verification.refresh_from_db()
    assert RegistrationVerification.objects.eligible().only("id").get() == verification
    assert verification.verified_at is not None
    assert verification.completed_at is None


@pytest.mark.django_db
def test_verification_registration_verify_expires_code_after_use(
    first_party_app_client: OAuthClient,
) -> None:
    verification = RegistrationVerificationFactory.create(code="123456")
    url, payload = (
        reverse("api:v1:verification:registration-verify"),
        {"id": verification.pk, "code": "123456"},
    )
    r1 = first_party_app_client.post(url, data=payload)
    r2 = first_party_app_client.post(url, data=payload)
    assert r1.status_code == 204
    assert r2.status_code == 404


@pytest.mark.django_db
def test_verification_registration_verify_bad_code(
    first_party_app_client: OAuthClient,
) -> None:
    verification = RegistrationVerificationFactory.create(code="123456")
    response = first_party_app_client.post(
        reverse("api:v1:verification:registration-verify"),
        data={
            "id": verification.pk,
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_verification_registration_verify_expired_code(
    first_party_app_client: OAuthClient,
) -> None:
    past = timezone.now() - timedelta(seconds=settings.REGISTRATION_VERIFY_TIMEOUT + 10)
    verification = RegistrationVerificationFactory.create(
        created_at=past,
        code="123456",
    )

    response = first_party_app_client.post(
        reverse("api:v1:verification:registration-verify"),
        data={
            "id": verification.pk,
            "code": "123456",
        },
    )
    assert response.status_code == 404
