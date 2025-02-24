from typing import TYPE_CHECKING, Any

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext, gettext_lazy as _

from rest_framework import exceptions, pagination, serializers
from rest_framework.fields import Field
from rest_framework.metadata import BaseMetadata
from rest_framework.mixins import UpdateModelMixin
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as default_exception_handler

from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema_field

if TYPE_CHECKING:
    from rest_framework.views import APIView


def to_errors(
    detail: list[Any] | dict[str, Any],
) -> list[Any] | dict[str, Any]:
    # Converts `ValidationError` instances to `errors` format, displayed in
    # API errors. This is quite similar to `exc.get_full_details()` except it
    # always ensures errors are in a list.
    if isinstance(detail, list):
        return [to_errors(item) for item in detail]
    if isinstance(detail, dict):
        return {
            key: to_errors([value] if isinstance(value, str) else value)
            for key, value in detail.items()
        }
    return {"message": detail, "code": detail.code}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Replaces the default exception handler with a more structured one.
    """

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = default_exception_handler(exc, context)
    if response is None:
        # In case the exception is not a subclass of `APIException`,
        # default to `handler500` implementation.
        return None
    assert isinstance(exc, exceptions.APIException)

    template = {
        "status": exc.status_code,
        "code": getattr(exc.detail, "code", exc.default_code),
        "message": exc.detail,
    }

    if isinstance(exc, exceptions.ValidationError):
        # ValidationError's raised in serializer methods like create() and
        # update() should behave as if they were raised in validate().
        details = to_errors(exc.detail)
        if isinstance(details, list):
            details = {api_settings.NON_FIELD_ERRORS_KEY: details}
        template["message"] = gettext(
            "One or more parameters to your request was invalid."
        )
        template["errors"] = details

    response.data = template
    return response


_pagination_map = {
    "page_number": pagination.PageNumberPagination,
    "cursor": pagination.CursorPagination,
    "limit_offset": pagination.LimitOffsetPagination,
}


def get_paginator(name: str = "page_number", /, **kwargs: Any) -> type[BasePagination]:
    kwargs.setdefault("page_size", 10)
    klass = _pagination_map[name]
    return type("Factory%s" % klass.__name__, (klass,), kwargs)


class DynamicFieldsMixin:
    # Allows creating of serializer fields selectively by passing 'fields'
    # keyword argument.

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert isinstance(self, serializers.Serializer)
        fields = kwargs.pop("fields", None)
        ref_name = kwargs.pop("ref_name", None)

        if fields is not None:
            assert ref_name, "ref_name is required when specifying fields"
        self.ref_name = ref_name
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed, existing = set(fields), set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class PartialUpdateModelMixin:
    """
    Update a model instance.

    rest_framework.mixins.UpdateModelMixin with 'PUT' disabled, i.e.,
    only allows for partial updates 'PATCH'.
    """

    perform_update = UpdateModelMixin.perform_update

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        kwargs["partial"] = True
        return UpdateModelMixin.update(self, request, *args, **kwargs)  # type: ignore[arg-type]


class EmptyMetadata(BaseMetadata):
    def determine_metadata(self, request: Request, view: "APIView") -> None:
        return None


class EmptySerializer(serializers.Serializer[None]):
    # Response serializer in views which yield 204 No Content.
    # Request serializer in views which do not require a body.
    pass


class ErrorDetail(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField()
    code = serializers.CharField()


class Errors(serializers.Serializer[dict[str, Any]]):
    non_field_errors = ErrorDetail(
        many=True,
        required=False,
        help_text="If errors are not related to specific parameters, this"
        " key might be present to contain other kinds of errors.",
    )
    field_name = ErrorDetail(  # type: ignore[assignment]
        many=True,
        required=False,
        help_text="Contains errors related to `field_name` parameter."
        " Number of such keys might vary.",
    )


class APIError(serializers.Serializer[dict[str, Any]]):
    # Generic error serializer for documentation rendering.
    status = serializers.IntegerField(
        min_value=100,
        max_value=599,
        help_text="HTTP status code.",
    )
    code = serializers.CharField(help_text="A code identifying the class of the error.")
    message = serializers.CharField(help_text="Human readable summary of the error.")
    errors = Errors(  # type: ignore[assignment]
        required=False,
        help_text="A mapping with the keys referencing the given parameters.",
    )


@extend_schema_field(
    serializers.CharField(
        help_text=_("Multiple values may be separated by commas."),
    )
)
class IDFilter(filters.Filter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("field_name", "id")
        kwargs.setdefault("lookup_expr", "in")
        kwargs.setdefault("base_field", forms.IntegerField(min_value=1))
        kwargs.setdefault("max_length", 50)
        super().__init__(*args, **kwargs)

    field_class = SimpleArrayField


class ContextDefault:
    """
    Get default value from serializer context.
    """

    requires_context = True

    def __init__(self, key: str) -> None:
        self.key = key

    def __call__(self, serializer_field: Field) -> Any:  # type: ignore[type-arg]
        return serializer_field.context[self.key]

    def __repr__(self) -> str:
        return "%s(key=%s)" % (self.__class__.__name__, self.key)
