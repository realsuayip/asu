from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from zeynep.utils.file import FileSizeValidator, MimeTypeValidator


class TestFileUtils(TestCase):
    @classmethod
    def setUpClass(cls):
        file_path = settings.BASE_DIR / "tests/files/asli.jpeg"
        cls.image = open(file_path, "rb")

    @classmethod
    def tearDownClass(cls):
        cls.image.close()

    def test_mimetype_validator(self):
        validate = MimeTypeValidator(allowed_types=["image/jpeg"])

        try:
            validate(self.image)
        except ValidationError:
            self.fail("unexpected validation error")

        validate.allowed_types = ["image/png"]
        with self.assertRaises(ValidationError):
            validate(self.image)

    def test_filesize_validator(self):
        validate = FileSizeValidator(max_size=16400)
        image = SimpleUploadedFile(
            self.image.name,
            self.image.read(),
            content_type="image/jpeg",
        )

        try:
            validate(image)
        except ValidationError:
            self.fail("unexpected validation error")

        validate.max_size = 11200
        with self.assertRaises(ValidationError):
            validate(image)
