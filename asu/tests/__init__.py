from django.test import TestCase

from asu.models import ProjectVariable


class TestProjectVariable(TestCase):
    def test_get_value_build(self):
        value = ProjectVariable.objects.get_value(name="build.BRAND")
        self.assertEqual("asu", value)

    def test_get_value_db(self):
        ProjectVariable.objects.create(name="HELLO_KITTY", value="im pink")

        value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
        self.assertEqual("im pink", value)

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
