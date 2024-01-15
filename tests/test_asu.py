from typing import Any, Callable, NoReturn
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.test import TestCase
from django.urls import reverse

from asu.models import ProjectVariable
from asu.utils.cache import build_vary_key


def error_view(exc: type[Exception]) -> Callable[..., NoReturn]:
    def view(*args: Any, **kwargs: Any) -> NoReturn:
        raise exc

    return view


class TestProjectVariable(TestCase):
    def test_get_value_build(self):
        value = ProjectVariable.objects.get_value(name="build.BRAND")
        self.assertEqual("asu", value)

    def test_get_value_db(self):
        ProjectVariable.objects.create(name="HELLO_KITTY", value="im pink")

        value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
        self.assertEqual("im pink", value)
        self.assertEqual(
            "im pink",
            cache.get(build_vary_key("variable", "name", "HELLO_KITTY")),
        )

    def test_get_value_db_cache_invalidates_on_save(self):
        var = ProjectVariable.objects.create(name="HELLO_KITTY", value="im pink")

        value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
        self.assertEqual("im pink", value)
        self.assertEqual(
            "im pink", cache.get(build_vary_key("variable", "name", "HELLO_KITTY"))
        )

        var.value = "im blue"
        var.save(update_fields=["value"])

        self.assertIsNone(cache.get(build_vary_key("variable", "name", "HELLO_KITTY")))

        new_value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
        self.assertEqual("im blue", new_value)
        self.assertEqual(
            "im blue", cache.get(build_vary_key("variable", "name", "HELLO_KITTY"))
        )

    def test_get_value_exceptions(self):
        cases = {
            "bad.GUY": "should contain a valid prefix",
            "badGUY": "should contain a valid prefix",
            "db.IM_NOT_HERE": "could not be found in the database",
            "build.IM_NOT_HERE": "IM_NOT_HERE",
        }

        for name, exc in cases.items():
            with self.assertRaisesRegex(KeyError, exc):
                ProjectVariable.objects.get_value(name=name)


class TestAPIRoot(TestCase):
    def test_api_root(self):
        url = reverse("api:api-root")

        response = self.client.get(url)
        content = response.json()

        self.assertEqual(200, response.status_code)

        self.assertIn("ip", content)
        self.assertIn("user-agent", content)
        self.assertIn("version", content)
        self.assertIn("docs", content)
        self.assertIn("schema", content)
        self.assertNotIn("routes", content)

        # Include routes.
        response = self.client.get(url, {"routes": "1"})
        content = response.json()
        self.assertIn("routes", content)

    def test_not_found(self):
        expected_json = {
            "status": 404,
            "code": "not_found",
            "message": "Not found.",
        }
        response = self.client.get("bad-page")

        # HTML
        self.assertContains(
            response,
            "requested resource was not found on this server",
            status_code=404,
        )
        self.assertIn("text/html", response.headers["Content-Type"])

        # JSON with /api/ prefix
        response = self.client.get("/api/bad-page")
        self.assertEqual(404, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(expected_json, response.json())

        # JSON with request Accept
        response = self.client.get("bad-page", headers={"Accept": "application/json"})
        self.assertEqual(404, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(expected_json, response.json())

    def test_bad_request(self):
        expected_json = {
            "status": 400,
            "code": "invalid",
            "message": "We could not handle your request. Please try again later.",
        }

        with patch("asu.views.APIRootView.get", error_view(SuspiciousOperation)):
            response = self.client.get(reverse("api:api-root"))

        self.assertEqual(400, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(expected_json, response.json())

        # Test HTML version
        with patch("two_factor.views.LoginView.get", error_view(SuspiciousOperation)):
            response = self.client.get(reverse("two_factor:login"))
            self.assertContains(
                response,
                "We could not handle your request",
                status_code=400,
            )

    def test_server_error(self):
        # To properly test server error case, change client instance
        # so that exceptions are not propagated to the test.
        client = self.client_class(raise_request_exception=False)
        expected_json = {
            "status": 500,
            "code": "server_error",
            "message": "We could not handle your request. Please try again later.",
        }

        with patch("asu.views.APIRootView.get", error_view(ZeroDivisionError)):
            response = client.get(
                reverse("api:api-root"), raise_request_exception=False
            )

        self.assertEqual(500, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(expected_json, response.json())

        # Test HTML version
        with patch("two_factor.views.LoginView.get", error_view(ZeroDivisionError)):
            response = client.get(reverse("two_factor:login"))
            self.assertContains(
                response,
                "We could not handle your request",
                status_code=500,
            )

    def test_permission_denied(self):
        expected_json = {
            "status": 403,
            "code": "permission_denied",
            "message": "You do not have permission to perform this action.",
        }

        # Since REST framework automatically handles PermissionDenied cases,
        # use non-API view with explict accept headers to simulate this error.
        with patch("two_factor.views.LoginView.get", error_view(PermissionDenied)):
            response = self.client.get(
                reverse("two_factor:login"),
                headers={"Accept": "application/json"},
            )

        self.assertEqual(403, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(expected_json, response.json())

        # Test HTML version
        with patch("two_factor.views.LoginView.get", error_view(PermissionDenied)):
            response = self.client.get(reverse("two_factor:login"))
            self.assertContains(
                response,
                "You do not have permission to perform this action",
                status_code=403,
            )

    def test_error_unknown_content_type(self):
        response = self.client.get(
            "bad-page", headers={"Accept": "application/unknown"}
        )
        self.assertContains(
            response,
            "requested resource was not found on this server",
            status_code=404,
        )
        self.assertIn("text/html", response.headers["Content-Type"])

    def test_docs(self):
        browser = reverse("docs:browse")
        schema = reverse("docs:openapi-schema")

        r1 = self.client.get(browser)
        r2 = self.client.get(schema)

        self.assertEqual(200, r1.status_code)
        self.assertEqual(200, r2.status_code)

    def test_empty_metadata(self):
        response = self.client.options(reverse("api:api-root"))
        self.assertEqual(b"", response.content)
