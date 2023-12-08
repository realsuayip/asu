from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from asu.models import ProjectVariable
from asu.utils.cache import build_vary_key


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
        self.assertIn("routes", content)
        self.assertIn("user-agent", content)
        self.assertIn("version", content)

    def test_alternating_error_page(self):
        response = self.client.get("bad-page")

        self.assertEqual(404, response.status_code)
        self.assertIn("text/html", response.headers["Content-Type"])

        response = self.client.get("/api/bad-page")
        self.assertEqual(404, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])

        response = self.client.get("bad-page", CONTENT_TYPE="application/json")
        self.assertEqual(404, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])

    def test_docs(self):
        browser = reverse("docs:browse")
        schema = reverse("docs:openapi-schema")

        r1 = self.client.get(browser)
        r2 = self.client.get(schema)

        self.assertEqual(200, r1.status_code)
        self.assertEqual(200, r2.status_code)
