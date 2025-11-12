from collections.abc import Callable
from typing import Any, NoReturn

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.urls import reverse

import pytest
from pytest_django.asserts import assertContains
from pytest_mock import MockerFixture

from tests.conftest import OAuthClient


def error_view(exc: type[Exception]) -> Callable[..., NoReturn]:
    def view(*args: Any, **kwargs: Any) -> NoReturn:
        raise exc

    return view


def test_custom_not_found_error_page(client: OAuthClient) -> None:
    # JSON with /api/ prefix
    # JSON with `Accept` header
    for resp in (
        client.get("/api/bad-page"),
        client.get("bad-page", headers={"Accept": "application/json"}),
    ):
        assert resp.status_code == 404
        assert "application/json" in resp.headers["Content-Type"]
        assert resp.json() == {
            "status": 404,
            "code": "not_found",
            "message": "Not found.",
        }

    # HTML version
    response = client.get("bad-page")
    assertContains(
        response,
        "requested resource was not found on this server",
        status_code=404,
    )
    assert "text/html" in response.headers["Content-Type"]


@pytest.mark.django_db
def test_custom_bad_request_page(client: OAuthClient, mocker: MockerFixture) -> None:
    # JSON version
    mocker.patch("asu.core.views.APIRootView.get", error_view(SuspiciousOperation))
    response = client.get(reverse("api:api-root"))
    assert response.status_code == 400
    assert "application/json" in response.headers["Content-Type"]
    assert response.json() == {
        "status": 400,
        "code": "invalid",
        "message": "We could not handle your request. Please try again later.",
    }

    # HTML version
    mocker.patch("two_factor.views.LoginView.get", error_view(SuspiciousOperation))
    response = client.get(reverse("two_factor:login"))
    assertContains(
        response,
        "We could not handle your request",
        status_code=400,
    )
    assert "text/html" in response.headers["Content-Type"]


def test_custom_server_error_page(mocker: MockerFixture) -> None:
    # To properly test server error case, change client instance
    # so that exceptions are not propagated to the test.
    client = OAuthClient(raise_request_exception=False)

    # JSON version
    mocker.patch("asu.core.views.APIRootView.get", error_view(ZeroDivisionError))
    response = client.get(reverse("api:api-root"), raise_request_exception=False)

    assert response.status_code == 500
    assert "application/json" in response.headers["Content-Type"]
    assert response.json() == {
        "status": 500,
        "code": "server_error",
        "message": "We could not handle your request. Please try again later.",
    }

    # HTML version
    mocker.patch("two_factor.views.LoginView.get", error_view(ZeroDivisionError))
    response = client.get(reverse("two_factor:login"))
    assertContains(
        response,
        "We could not handle your request",
        status_code=500,
    )
    assert "text/html" in response.headers["Content-Type"]


@pytest.mark.django_db
def test_custom_permission_denied_page(
    client: OAuthClient, mocker: MockerFixture
) -> None:
    # JSON version
    mocker.patch("two_factor.views.LoginView.get", error_view(PermissionDenied))
    response = client.get(
        reverse("two_factor:login"),
        # Since REST framework automatically handles PermissionDenied cases,
        # use non-API view with explict `Accept` header to simulate this error.
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 403
    assert "application/json" in response.headers["Content-Type"]
    assert response.json() == {
        "status": 403,
        "code": "permission_denied",
        "message": "You do not have permission to perform this action.",
    }

    # HTML version
    response = client.get(reverse("two_factor:login"))
    assertContains(
        response,
        "You do not have permission to perform this action",
        status_code=403,
    )
    assert "text/html" in response.headers["Content-Type"]


def test_error_page_with_unknown_content_type_header(client: OAuthClient) -> None:
    # When custom error pages encounter an unknown content type in `Accept`
    # header, they should default to HTML. Paths that start with `/api/` should
    # return JSON as usual.
    response = client.get(
        "bad-page",
        headers={"Accept": "application/unknown"},
    )
    assert response.status_code == 404
    assert "text/html" in response.headers["Content-Type"]

    response_json = client.get(
        "/api/bad-page",
        headers={"Accept": "application/unknown"},
    )
    assert response_json.status_code == 404
    assert "application/json" in response_json.headers["Content-Type"]
