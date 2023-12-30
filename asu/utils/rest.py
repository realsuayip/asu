from typing import TYPE_CHECKING, Any

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext, gettext_lazy as _

from rest_framework import exceptions, pagination, serializers
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
        "code": exc.default_code,
        "message": exc.detail,
    }

    if isinstance(exc, exceptions.ValidationError):
        # ValidationError's raised in serializer methods like create() and
        # update() should behave as if they were raised in validate().
        template["message"] = gettext(
            "One or more parameters to your request was invalid."
        )
        detail: Any = exc.detail

        if isinstance(detail, dict):
            non_field_errors = detail.pop(api_settings.NON_FIELD_ERRORS_KEY, None)
            for key, value in detail.items():
                if isinstance(value, str):
                    detail[key] = [value]
                else:
                    detail[key] = value
            detail = detail or non_field_errors

        if detail:
            template["errors"] = detail

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


class APIError(serializers.Serializer[dict[str, Any]]):
    # Generic error serializer for documentation rendering.
    status = serializers.IntegerField(
        min_value=100,
        max_value=599,
        help_text="HTTP status code.",
    )
    code = serializers.CharField(help_text="A code identifying the class of the error.")
    message = serializers.CharField(help_text="Human readable summary of the error.")
    errors = serializers.JSONField(  # type: ignore[assignment]
        required=False,
        help_text="This could be a list of errors, or a mapping with the"
        " keys referencing the given parameters.",
    )


@extend_schema_field(
    serializers.ListField(
        child=serializers.IntegerField(min_value=1),
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
