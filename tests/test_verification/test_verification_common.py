import uuid

from django.apps import apps
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.regex_helper import _lazy_re_compile

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks
from pytest_mock import MockerFixture

from asu.auth.models import User
from tests.conftest import OAuthClient
from tests.factories import (
    RegistrationVerificationFactory,
    UserFactory,
)

EMAIL_CODE_REGEX = _lazy_re_compile(r"<div class='code'><strong>(\d+)</strong></div>")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    (
        "verification.EmailVerification",
        "verification.RegistrationVerification",
        "verification.PasswordResetVerification",
    ),
)
@override_settings(VERIFICATION_SECRET_KEY="secret")
def test_code_generation(
    mocker: MockerFixture,
    model: str,
    user: User,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    klass = apps.get_model(model)
    mocker.patch(
        "asu.verification.models.base.get_random_string",
        return_value="123456",
    )
    with django_capture_on_commit_callbacks(execute=True):
        klass.objects.start(
            pk=uuid.UUID("019ee4bce367772f817c9ad0e358c6cf"),
            email=user.email,
            user=user,
        )
    code = EMAIL_CODE_REGEX.search(mail.outbox[0].body).group(1)
    obj = klass.objects.get()
    assert (
        obj.code_hash
        == "ad73700bc37a183bfe895893392cd80931649356c535d878323e2ed6afe8b072"
    )
    assert code == "123456"


@pytest.mark.django_db
def test_code_generation_same_code() -> None:
    v1, v2 = RegistrationVerificationFactory.create_batch(
        code="123456",
        size=2,
    )
    assert v1.code_hash != v2.code_hash


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:v1:verification:registration-verify",
        "api:v1:verification:password-reset-verify",
        "api:v1:verification:email-change-complete",
    ),
)
def test_verification_verify_missing(
    first_party_app_client: OAuthClient,
    endpoint: str,
) -> None:
    if endpoint == "api:v1:verification:email-change-complete":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("code", ("9876544", "AB34511", "112"))
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:v1:verification:registration-verify",
        "api:v1:verification:password-reset-verify",
        "api:v1:verification:email-change-complete",
    ),
)
def test_verification_verify_invalid_code(
    first_party_app_client: OAuthClient,
    endpoint: str,
    code: str,
) -> None:
    if endpoint == "api:v1:verification:email-change-complete":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"]["code"] == [
        {
            "code": "invalid",
            "message": "Please enter a valid code.",
        }
    ]


@pytest.mark.parametrize(
    "endpoint",
    (
        "api:v1:verification:registration-verify",
        "api:v1:verification:password-reset-verify",
        "api:v1:verification:email-change-complete",
    ),
)
def test_verification_verify_requires_authentication(
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "123456",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:v1:verification:registration-verify",
        "api:v1:verification:password-reset-verify",
        "api:v1:verification:email-change-complete",
    ),
)
def test_verification_verify_requires_first_party_app(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "123456",
        },
    )
    assert response.status_code == 403
