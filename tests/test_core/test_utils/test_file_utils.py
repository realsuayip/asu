from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from asu.core.utils.file import FileSizeValidator, MimeTypeValidator


@pytest.fixture
def sample_image(pytestconfig: pytest.Config) -> SimpleUploadedFile:
    path = pytestconfig.rootpath / "tests/fixtures/sample_profile_picture.jpeg"
    with path.open("rb") as f:
        return SimpleUploadedFile(
            name="sample.jpeg",
            content=f.read(),
            content_type="image/jpeg",
        )


def test_mimetype_validator(sample_image: SimpleUploadedFile) -> None:
    validate = MimeTypeValidator(allowed_types=["image/jpeg"])
    validate(sample_image)

    validate.allowed_types = ["image/png"]
    with pytest.raises(ValidationError):
        validate(sample_image)

    invalid_image = SimpleUploadedFile("test.png", b"test", "image/png")
    with pytest.raises(ValidationError):
        validate(invalid_image)


def test_filesize_validator(sample_image: SimpleUploadedFile) -> None:
    validate = FileSizeValidator(max_size=16400)
    validate(sample_image)

    validate.max_size = 11200
    with pytest.raises(ValidationError):
        validate(sample_image)
