import mimetypes
import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

import magic


def get_mime_type(file):
    initial_pos = file.tell()
    file.seek(0)
    mime_type = magic.from_buffer(file.read(1024), mime=True)
    file.seek(initial_pos)
    return mime_type


@deconstructible
class MimeTypeValidator:
    message = _("The file you uploaded did not have the valid mime type.")

    def __init__(self, allowed_types):
        self.allowed_types = allowed_types

    def __call__(self, file):
        # First, guess the mimetype, if it doesn't match,
        # don't bother invoking magic.
        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type not in self.allowed_types:
            raise ValidationError(self.message)

        mime_type = get_mime_type(file)
        if mime_type not in self.allowed_types:
            raise ValidationError(self.message)


@deconstructible
class FileSizeValidator:
    message = _(
        "The size of the file you uploaded exceeded the maximum limit."
    )

    def __init__(self, max_size):
        self.max_size = max_size

    def __call__(self, file):
        if file.size > self.max_size:
            raise ValidationError(self.message)


@deconstructible
class UserContentPath:
    base_path = "usercontent/"

    def __init__(self, template):
        self.template = self.base_path + template

    def __call__(self, instance, filename):
        _, ext = os.path.splitext(filename)
        return self.template.format(
            instance=instance, uuid=uuid.uuid4().hex, ext=ext
        )
