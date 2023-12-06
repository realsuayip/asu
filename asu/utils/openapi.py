from typing import Any

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import Direction

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
