from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Any, AnyStr

from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.exceptions import ValidationError
from django.core.files import File
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

import magic
from storages.backends.s3boto3 import S3Boto3Storage, S3ManifestStaticStorage


def get_mime_type(file: File[AnyStr]) -> str:
    initial_pos = file.tell()
    file.seek(0)
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(initial_pos)
    return mime_type


@deconstructible
class MimeTypeValidator:
    message = _("The file you uploaded did not have the valid mime type.")

    def __init__(self, allowed_types: list[str]) -> None:
        self.allowed_types = allowed_types

    def __call__(self, file: File[AnyStr]) -> None:
        # First, guess the mimetype, if it doesn't match,
        # don't bother invoking magic.
        name = file.name or ""
        mime_type, _ = mimetypes.guess_type(name)

        if mime_type not in self.allowed_types:
            raise ValidationError(self.message)

        mime_type = get_mime_type(file)
        if mime_type not in self.allowed_types:
            raise ValidationError(self.message)


@deconstructible
class FileSizeValidator:
    message = _("The size of the file you uploaded exceeded the maximum limit.")

    def __init__(self, max_size: int):
        self.max_size = max_size

    def __call__(self, file: File[AnyStr]) -> None:
        if file.size > self.max_size:
            raise ValidationError(self.message)


@deconstructible
class UserContentPath:
    base_path = "usercontent/"

    def __init__(self, template: str) -> None:
        self.template = self.base_path + template

    def __call__(self, instance: Any, filename: str) -> str:
        _, ext = os.path.splitext(filename)
        return self.template.format(instance=instance, uuid=uuid.uuid4().hex, ext=ext)


class S3StaticStorage(S3ManifestStaticStorage):
    location = "static"
    default_acl = "public-read"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Store `staticfiles.json` in local filesystem so that no
        # additional requests are made to remote file storage just to
        # fetch file mappings.
        manifest_storage = StaticFilesStorage(location=settings.BASE_DIR / "static")
        super().__init__(*args, manifest_storage=manifest_storage, **kwargs)


class S3MediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "private"
