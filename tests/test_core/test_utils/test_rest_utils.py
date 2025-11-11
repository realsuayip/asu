from django.urls import reverse

from rest_framework import exceptions
from rest_framework.exceptions import ErrorDetail

import pytest

from asu.core.utils.rest import exception_handler
from tests.conftest import OAuthClient

exception_handler_cases = (
    pytest.param(
        exceptions.NotAuthenticated(),
        {
            "status": 401,
            "code": "not_authenticated",
            "message": exceptions.NotAuthenticated.default_detail,
        },
        id="not_authenticated",
    ),
    pytest.param(
        exceptions.MethodNotAllowed("GET"),
        {
            "status": 405,
            "code": "method_not_allowed",
            "message": exceptions.MethodNotAllowed.default_detail.format(method="GET"),
        },
        id="method_not_allowed",
    ),
    pytest.param(
        exceptions.NotFound(),
        {
            "status": 404,
            "code": "not_found",
            "message": exceptions.NotFound.default_detail,
        },
        id="not_found",
    ),
    pytest.param(
        exceptions.PermissionDenied(),
        {
            "status": 403,
            "code": "permission_denied",
            "message": exceptions.PermissionDenied.default_detail,
        },
        id="permission_denied",
    ),
    pytest.param(
        exceptions.PermissionDenied(code="otp_required"),
        {
            "status": 403,
            "code": "otp_required",
            "message": exceptions.PermissionDenied.default_detail,
        },
        id="permission_denied_custom_code",
    ),
    pytest.param(
        exceptions.ValidationError("some message"),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "non_field_errors": [
                    {"message": "some message", "code": "invalid"},
                ]
            },
        },
        id="validation_error_simple",
    ),
    pytest.param(
        exceptions.ValidationError("some message", code="custom"),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "non_field_errors": [
                    {"message": "some message", "code": "custom"},
                ]
            },
        },
        id="validation_error_custom_code",
    ),
    pytest.param(
        exceptions.ValidationError(["multi", "messages"]),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "non_field_errors": [
                    {"message": "multi", "code": "invalid"},
                    {"message": "messages", "code": "invalid"},
                ]
            },
        },
        id="validation_error_multiple_messages",
    ),
    pytest.param(
        exceptions.ValidationError({"key": "value"}),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {"key": [{"message": "value", "code": "invalid"}]},
        },
        id="validation_error_dict",
    ),
    pytest.param(
        exceptions.ValidationError({"key": "value"}, code="custom"),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {"key": [{"message": "value", "code": "custom"}]},
        },
        id="validation_error_dict_custom_code",
    ),
    pytest.param(
        exceptions.ValidationError({"key": "value", "key2": ["value1", "value2"]}),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "key": [{"message": "value", "code": "invalid"}],
                "key2": [
                    {"message": "value1", "code": "invalid"},
                    {"message": "value2", "code": "invalid"},
                ],
            },
        },
        id="validation_error_nested_dict_list",
    ),
    pytest.param(
        exceptions.ValidationError({"non_field_errors": ["hey you"]}),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {"non_field_errors": [{"message": "hey you", "code": "invalid"}]},
        },
        id="validation_error_non_field_errors",
    ),
    pytest.param(
        exceptions.ValidationError({"key": {"value": "heyy"}}),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "key": {
                    "value": [{"message": "heyy", "code": "invalid"}],
                }
            },
        },
        id="validation_error_nested_dict",
    ),
    pytest.param(
        exceptions.ValidationError(
            [ErrorDetail("msg1", code="code1"), ErrorDetail("msg2", code="code2")]
        ),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "non_field_errors": [
                    {"message": "msg1", "code": "code1"},
                    {"message": "msg2", "code": "code2"},
                ]
            },
        },
        id="validation_error_multiple_codes",
    ),
    pytest.param(
        exceptions.ValidationError({"key1": ErrorDetail("msg1", code="code1")}),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {"key1": [{"message": "msg1", "code": "code1"}]},
        },
        id="validation_error_dict_custom_code",
    ),
    pytest.param(
        exceptions.ValidationError(
            {
                "key1": ErrorDetail("msg1", code="code1"),
                "key2": [
                    ErrorDetail("msg2", code="code2"),
                    ErrorDetail("msg3", code="code3"),
                ],
            }
        ),
        {
            "status": 400,
            "code": "invalid",
            "message": "One or more parameters to your request was invalid.",
            "errors": {
                "key1": [{"message": "msg1", "code": "code1"}],
                "key2": [
                    {"message": "msg2", "code": "code2"},
                    {"message": "msg3", "code": "code3"},
                ],
            },
        },
        id="validation_error_mixed_error_detail",
    ),
)


@pytest.mark.parametrize("exception, expected", exception_handler_cases)
def test_exception_handler(exception, expected):
    response = exception_handler(exception, {})
    assert response.data == expected


def test_empty_metadata(client: OAuthClient) -> None:
    response = client.options(reverse("api:api-root"))
    assert response.content == b""


def test_docs(client: OAuthClient) -> None:
    browser = reverse("docs:browse")
    schema = reverse("docs:openapi-schema")

    r1 = client.get(browser)
    assert r1.status_code == 200
    assert "text/html" in r1.headers["Content-Type"]

    r2 = client.get(schema)
    assert r2.status_code == 200
    assert "application/vnd.oai.openapi" in r2.headers["Content-Type"]


def test_api_root(client: OAuthClient) -> None:
    url = reverse("api:api-root")

    response = client.get(url, headers={"User-Agent": "test"})
    assert response.status_code == 200
    assert response.json() == {
        "version": "1.0",
        "secure": False,
        "ip": "127.0.0.1",
        "user-agent": "test",
        "docs": "http://testserver/docs/",
        "schema": "http://testserver/docs/schema/",
    }

    # Make sure route resolving logic works
    response = client.get(url, {"routes": "1"})
    content = response.json()
    assert "routes" in content
