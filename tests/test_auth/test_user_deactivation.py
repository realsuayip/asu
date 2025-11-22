import datetime
import zoneinfo

from django.core import mail
from django.db import IntegrityError
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django import DjangoCaptureOnCommitCallbacks
from pytest_mock import MockerFixture

from asu.auth.models import (
    AccessToken,
    Application,
    RefreshToken,
    Session,
    User,
    UserDeactivation,
)
from asu.auth.tasks import delete_users_permanently
from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_deactivate(
    user: User,
    user_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user.set_password("hello")
    user.save(update_fields=["password", "updated"])
    # Force a session login to create a session. All sessions must
    # be invalidated after deactivating the account.
    client = Client()
    client.force_login(user)
    # Create the refresh token for test client.
    access = user_client._oauth[user.pk]
    refresh_token = RefreshToken.objects.create(
        user=user,
        token="some-token",
        access_token=access,
        application=access.application,
    )
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = user_client.post(
            reverse("api:auth:user-deactivate"),
            data={"password": "hello"},
        )
    assert response.status_code == 204
    assert len(mail.outbox) == 0
    assert len(callbacks) == 0

    user.refresh_from_db()
    refresh_token.refresh_from_db()
    deactivation = UserDeactivation.objects.get(user=user)
    assert user.is_frozen is True
    assert not Session.objects.filter(user=user.pk).exists()
    assert not AccessToken.objects.filter(user=user).exists()
    assert deactivation.date_revoked is None
    assert deactivation.for_deletion is False
    assert refresh_token.revoked is not None


@pytest.mark.django_db
def test_user_deactivate_for_deletion(
    user: User,
    user_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    user.set_password("hello")
    user.save(update_fields=["password", "updated"])

    client = Client()
    client.force_login(user)

    access = user_client._oauth[user.pk]
    refresh_token = RefreshToken.objects.create(
        user=user,
        token="some-token",
        access_token=access,
        application=access.application,
    )
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = user_client.post(
            reverse("api:auth:user-deactivate"),
            data={
                "password": "hello",
                "for_deletion": True,
            },
        )
    assert response.status_code == 204
    assert len(mail.outbox) == 1
    assert len(callbacks) == 1
    assert "account has been deactivated" in mail.outbox[0].body

    user.refresh_from_db()
    refresh_token.refresh_from_db()
    deactivation = UserDeactivation.objects.get(user=user)
    assert user.is_frozen is True
    assert not Session.objects.filter(user=user.pk).exists()
    assert not AccessToken.objects.filter(user=user).exists()
    assert deactivation.date_revoked is None
    assert deactivation.for_deletion is True
    assert refresh_token.revoked is not None


@pytest.mark.django_db
def test_user_deactivate_invalid_password(user_client: OAuthClient) -> None:
    response = user_client.post(
        reverse("api:auth:user-deactivate"),
        data={"password": "rand"},
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "password": [
            {
                "code": "invalid",
                "message": "Your password was not correct.",
            }
        ]
    }


def test_user_deactivate_requires_authentication(client: OAuthClient) -> None:
    response = client.post(reverse("api:auth:user-deactivate"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_deactivate_requires_user_token(app_client: OAuthClient) -> None:
    response = app_client.post(reverse("api:auth:user-deactivate"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_deactivate_requires_first_party_token(
    user: User,
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    client.set_user(user, app=authorization_code_third_party_app)
    response = client.post(reverse("api:auth:user-deactivate"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_reactivate(user: User) -> None:
    user.deactivate()
    deactivation = UserDeactivation.objects.get(user=user)
    assert user.is_frozen is True
    assert deactivation.date_revoked is None

    user.reactivate()
    deactivation.refresh_from_db()
    assert user.is_frozen is False
    assert deactivation.date_revoked is not None


@pytest.mark.django_db
def test_user_reactivate_by_session_activity(
    user: User,
) -> None:
    # TODO: consider doing this in API level as well
    user.deactivate()
    deactivation = UserDeactivation.objects.get(user=user)

    client = Client()
    client.force_login(user)
    client.get(reverse("two_factor:profile"))

    user.refresh_from_db()
    deactivation.refresh_from_db()

    assert user.is_frozen is False
    assert deactivation.date_revoked is not None


@pytest.mark.django_db
def test_task_delete_users_permanently(mocker: MockerFixture) -> None:
    (
        delete_immediately,
        to_be_deleted_later,
        deletion_cancelled,
        not_for_deletion,
        _unrelated,
    ) = UserFactory.create_batch(5)

    now = datetime.datetime(2022, 1, 1, tzinfo=zoneinfo.ZoneInfo("UTC"))

    # This one should not trigger.
    UserDeactivation.objects.create(user=to_be_deleted_later, for_deletion=True)

    mocker.patch("django.utils.timezone.now", return_value=now)

    # These deactivations will be triggered immediately.
    UserDeactivation.objects.create(user=delete_immediately, for_deletion=True)
    UserDeactivation.objects.create(user=not_for_deletion, for_deletion=False)
    UserDeactivation.objects.create(
        user=deletion_cancelled, date_revoked=now, for_deletion=True
    )

    future = now + datetime.timedelta(days=30)
    mocker.patch("django.utils.timezone.now", return_value=future)
    num, objs = delete_users_permanently()
    assert num == 2
    assert objs["account.User"] == 1
    with pytest.raises(User.DoesNotExist):
        delete_immediately.refresh_from_db()


@pytest.mark.django_db
def test_user_deactivation_unique_constraint(user: User) -> None:
    UserDeactivation.objects.create(user=user, date_revoked=timezone.now())
    UserDeactivation.objects.create(user=user)
    with pytest.raises(IntegrityError):
        UserDeactivation.objects.create(user=user)
