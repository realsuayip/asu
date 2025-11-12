import pytest
from django_otp.models import Device

from asu.auth.models import AccessToken, RefreshToken, StaticDevice, TOTPDevice, User
from tests.conftest import create_default_application


@pytest.mark.django_db
def test_user_revoke_other_tokens(user: User) -> None:
    create_default_application()

    r1 = user.issue_token()
    r2 = user.issue_token()
    r3 = user.issue_token()

    current = AccessToken.objects.get(token=r3["access_token"])
    user.revoke_other_tokens(current)

    refresh1 = RefreshToken.objects.get(token=r1["refresh_token"])
    refresh2 = RefreshToken.objects.get(token=r2["refresh_token"])
    refresh_current = RefreshToken.objects.get(token=r3["refresh_token"])

    assert refresh1.revoked is not None
    assert refresh2.revoked is not None
    assert refresh_current.revoked is None
    assert AccessToken.objects.only("pk").get().pk == current.pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cls",
    (
        TOTPDevice,
        StaticDevice,
    ),
)
def test_user_two_factor_enabled(
    user: User,
    cls: Device,
) -> None:
    assert user.two_factor_enabled is False
    del user.two_factor_enabled

    cls.objects.create(user=user, confirmed=True)
    assert user.two_factor_enabled is True
