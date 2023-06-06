from unittest.mock import Mock

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from asu.utils.cache import cached_context
from asu.utils.file import FileSizeValidator, MimeTypeValidator


class TestFileUtils(TestCase):
    @classmethod
    def setUpClass(cls):
        file_path = settings.BASE_DIR.parent / "tests/files/asli.jpeg"
        cls.image = open(file_path, "rb")

    @classmethod
    def tearDownClass(cls):
        cls.image.close()

    def test_mimetype_validator(self):
        validate = MimeTypeValidator(allowed_types=["image/jpeg"])
        validate(self.image)

        validate.allowed_types = ["image/png"]
        with self.assertRaises(ValidationError):
            validate(self.image)

        invalid_image = SimpleUploadedFile("test.png", b"test", "image/png")
        with self.assertRaises(ValidationError):
            validate(invalid_image)

    def test_filesize_validator(self):
        validate = FileSizeValidator(max_size=16400)
        image = SimpleUploadedFile(
            self.image.name,
            self.image.read(),
            content_type="image/jpeg",
        )
        validate(image)

        validate.max_size = 11200
        with self.assertRaises(ValidationError):
            validate(image)


class TestCacheUtils(TestCase):
    def test_cached_context(self):
        mock = Mock()

        @cached_context(key="asu.test.my_func")
        def my_func() -> int:
            """Some function."""
            mock.compute()
            return 256

        self.assertEqual(256, my_func())
        self.assertEqual(256, my_func())
        mock.compute.assert_called_once()
        self.assertEqual(256, cache.get("asu.test.my_func"))
        self.assertEqual("Some function.", my_func.__doc__)
