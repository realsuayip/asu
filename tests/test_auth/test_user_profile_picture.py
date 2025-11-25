from django.core.files.base import ContentFile
from django.urls import reverse

import pytest

from asu.auth.models import Application, User
from tests.conftest import OAuthClient


@pytest.fixture
def sample_profile_picture(pytestconfig: pytest.Config) -> ContentFile:
    path = pytestconfig.rootpath / "tests/fixtures/sample_profile_picture.jpeg"
    with path.open("rb") as f:
        return ContentFile(f.read(), name="sample.jpeg")


@pytest.mark.django_db
def test_user_set_profile_picture(
    user: User,
    user_client: OAuthClient,
    sample_profile_picture: ContentFile,
) -> None:
    response = user_client.put(
        reverse("api:auth:user-profile-picture"),
        data={"profile_picture": sample_profile_picture},
        format="multipart",
    )
    path = response.json()["profile_picture"]
    assert response.status_code == 200
    assert f"/usercontent/{user.pk}/profile_picture" in path
    assert path.endswith(".jpeg")

    profile = user_client.get(
        reverse(
            "api:auth:user-detail",
            kwargs={"pk": user.pk},
        )
    )
    profile_picture_url = profile.json()["profile_picture"]
    assert profile_picture_url is not None
    assert "/cache/" in profile_picture_url
    assert profile_picture_url.endswith(".jpg")


@pytest.mark.django_db
def test_user_replace_profile_picture(
    user: User,
    user_client: OAuthClient,
    sample_profile_picture: ContentFile,
) -> None:
    user.profile_picture = sample_profile_picture
    user.save(update_fields=["profile_picture", "updated_at"])
    previous = user.profile_picture.path
    sample_profile_picture.seek(0)

    response = user_client.put(
        reverse("api:auth:user-profile-picture"),
        data={"profile_picture": sample_profile_picture},
        format="multipart",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert previous != user.profile_picture.path


@pytest.mark.django_db
def test_user_profile_picture_endpoints_require_authentication(
    client: OAuthClient,
) -> None:
    url = reverse("api:auth:user-profile-picture")
    r1 = client.put(url)
    r2 = client.delete(url)
    assert r1.status_code == r2.status_code == 401


@pytest.mark.django_db
def test_user_profile_picture_endpoints_require_user_token(
    app_client: OAuthClient,
) -> None:
    url = reverse("api:auth:user-profile-picture")
    r1 = app_client.put(url)
    r2 = app_client.delete(url)
    assert r1.status_code == r2.status_code == 403


@pytest.mark.django_db
def test_user_profile_picture_endpoints_require_first_party_app(
    user: User,
    client: OAuthClient,
    authorization_code_third_party_app: Application,
) -> None:
    client.set_user(user, app=authorization_code_third_party_app)
    url = reverse("api:auth:user-profile-picture")
    r1 = client.put(url)
    r2 = client.delete(url)
    assert r1.status_code == r2.status_code == 403


@pytest.mark.django_db
def test_user_delete_profile_picture(
    user: User,
    user_client: OAuthClient,
    sample_profile_picture: ContentFile,
) -> None:
    user.profile_picture = sample_profile_picture
    user.save(update_fields=["profile_picture", "updated_at"])

    response = user_client.delete(
        reverse("api:auth:user-profile-picture"),
    )
    assert response.status_code == 204
    user.refresh_from_db()
    assert not bool(user.profile_picture)


@pytest.mark.django_db
def test_user_delete_profile_picture_ok_if_not_previously_exists(
    user_client: OAuthClient,
) -> None:
    response = user_client.delete(reverse("api:auth:user-profile-picture"))
    assert response.status_code == 204
