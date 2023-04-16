from typing import TYPE_CHECKING, Any, Type

from rest_framework import exceptions, pagination, serializers
from rest_framework.metadata import BaseMetadata
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as default_exception_handler

if TYPE_CHECKING:
    from rest_framework.views import APIView


def exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    response = default_exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        # ValidationError's raised in serializer methods like create() and
        # update() should behave as if they were raised in validate().
        non_field_errors = api_settings.NON_FIELD_ERRORS_KEY

        if isinstance(exc.detail, list):
            response.data = {non_field_errors: exc.detail}
        elif isinstance(exc.detail, dict):
            detail = {}
            for key, value in exc.detail.items():
                if isinstance(value, str):
                    value = [value]
                detail[key] = value
            response.data = detail

    return response


_pagination_map = {
    "page_number": pagination.PageNumberPagination,
    "cursor": pagination.CursorPagination,
    "limit_offset": pagination.LimitOffsetPagination,
}


def get_paginator(
    name: str = "page_number", /, **kwargs: Any
) -> Type[BasePagination]:
    kwargs.setdefault("page_size", 10)
    klass = _pagination_map[name]
    return type("Factory%s" % klass.__name__, (klass,), kwargs)


class DynamicFieldsMixin:
    """
    Allows creating of serializer fields selectively by passing 'fields'
    keyword argument.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert isinstance(self, serializers.Serializer)
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed, existing = set(fields), set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class EmptyMetadata(BaseMetadata):
    def determine_metadata(self, request: Request, view: "APIView") -> None:
        return None


class APIError(serializers.Serializer[dict[str, Any]]):
    # Generic error serializer for documentation rendering.
    detail = serializers.CharField()
