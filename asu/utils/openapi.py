import types
from typing import Any

from django.utils.translation import gettext_lazy as _

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import Direction, OpenApiExample

from asu.utils.rest import DynamicFieldsMixin


class DynamicFieldsModelSerializerExtension(OpenApiSerializerExtension):
    target_class = DynamicFieldsMixin
    match_subclasses = True

    def map_serializer(self, auto_schema: AutoSchema, direction: Direction) -> Any:
        return auto_schema._map_serializer(  # type: ignore[no-untyped-call]
            self.target, direction, bypass_extensions=True
        )

    def get_name(self, auto_schema: AutoSchema, direction: Direction) -> Any:
        return self.target.ref_name


def get_error_repr(errors: Any) -> dict[str, Any]:
    # Create an error response representation from given
    # errors. Used in OpenAPI examples.
    return {
        "status": 400,
        "code": "invalid",
        "message": "One or more parameters to your request was invalid.",
        "errors": errors,
    }


examples = types.SimpleNamespace(
    not_found=OpenApiExample(
        "resource was not found",
        value={
            "status": 404,
            "code": "not_found",
            "message": _("Not found."),
        },
        response_only=True,
        status_codes=["404"],
    ),
    permission_denied=OpenApiExample(
        "access to resource was denied",
        value={
            "status": 403,
            "code": "permission_denied",
            "message": _("You do not have permission to perform this action."),
        },
        response_only=True,
        status_codes=["403"],
    ),
)
