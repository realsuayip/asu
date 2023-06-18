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


class CustomAutoSchema(AutoSchema):
    def get_filter_backends(self) -> Any:
        # Display query parameters for filters if the action/view
        # defines `filter_backends`.
        return getattr(self.view, "filter_backends", [])
