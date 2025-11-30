import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoAssertNumQueries, DjangoCaptureOnCommitCallbacks
from pytest_mock import MockerFixture

from asu.core.utils import messages
from asu.verification.models import PasswordResetVerification
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_password_reset_complete(
    first_party_app_client: OAuthClient,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    payload = {
        "id": verification.pk,
        "password": "hln_j1070",
    }
    with django_assert_num_queries(
        2  # savepoint
        + 1  # fetch token
        + 1  # fetch verification
        + 1  # update verification
        + 2  # null others
        + 1  # set password
        + 1  # fetch user tokens for invalidation
        + 1  # fetch user sessions for invalidation
    ):
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-complete"),
            data=payload,
        )
    assert response.status_code == 204

    user.refresh_from_db()
    assert user.check_password("hln_j1070")

    verification.refresh_from_db()
    assert verification.completed_at is not None


@pytest.mark.django_db
def test_user_password_reset_complete_case_invalid_id(
    first_party_app_client: OAuthClient,
) -> None:
    payload = {
        "id": uuid.uuid7(),
        "password": "Hln_1900",
    }
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
        data=payload,
    )
    assert response.status_code == 404
    assert response.json()["message"] == messages.BAD_VERIFICATION_ID


@pytest.mark.django_db
def test_user_password_reset_complete_case_expired_id(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    mocker.patch(
        "django.utils.timezone.now",
        return_value=timezone.now()
        + timedelta(seconds=settings.PASSWORD_RESET_COMPLETE_TIMEOUT + 1),
    )
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": verification.pk,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 404
    assert response.json()["message"] == messages.BAD_VERIFICATION_ID


@pytest.mark.django_db
def test_user_password_reset_complete_case_unusable_password(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": verification.pk,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 404
    assert response.json()["message"] == messages.BAD_VERIFICATION_ID


@pytest.mark.django_db
def test_user_password_reset_complete_password_validation(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    verification = PasswordResetVerification.objects.create(
        user=user,
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    payload = {
        "id": verification.pk,
        "password": "helenexample",
    }
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
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


def test_user_password_reset_complete_requires_authentication(
    client: OAuthClient,
) -> None:
    response = client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": uuid.uuid7(),
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_password_reset_complete_requires_requires_first_party_app(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": uuid.uuid7(),
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_password_reset_complete_nullifies_other_verifications(
    first_party_app_client: OAuthClient,
) -> None:
    user = UserFactory.create(email="helen@example.com")
    v1, v2, v3 = PasswordResetVerification.objects.bulk_create(
        [
            PasswordResetVerification(
                email="helen@example.com",
                user=user,
                verified_at=timezone.now(),
                code="111111",
            ),
            PasswordResetVerification(
                email="helen@example.com",
                user=user,
                verified_at=timezone.now(),
                code="111112",
            ),
            PasswordResetVerification(
                email="helen@example.com",
                user=user,
                code="111113",
            ),
        ]
    )
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": v1.pk,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 204

    v1.refresh_from_db()
    v2.refresh_from_db()
    v3.refresh_from_db()

    assert v1.completed_at is not None
    assert v2.nulled_by == v3.nulled_by == v1


@pytest.mark.django_db
def test_user_password_reset_flow(
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user = UserFactory.create(email="helen@example.com")

    # Step 1: Send verification email containing code
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:password-reset-send"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    uid = response.json()["id"]
    code = re.search(
        r"<div class='code'><strong>(\d+)</strong></div>",
        mail.outbox[0].body,
    ).group(1)

    # Step 2: Pair id with code to verify it
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-verify"),
        data={
            "id": uid,
            "code": code,
        },
    )
    assert response.status_code == 204

    # Step 3: Reset password with verified id
    response = first_party_app_client.post(
        reverse("api:verification:password-reset-complete"),
        data={
            "id": uid,
            "password": "Hln_1900",
        },
    )
    assert response.status_code == 204

    user.refresh_from_db()
    assert user.check_password("Hln_1900")
