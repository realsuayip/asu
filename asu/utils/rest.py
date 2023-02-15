from rest_framework import exceptions, pagination, serializers
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as default_exception_handler


def exception_handler(exc, context):
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


def get_paginator(name="page_number", /, **kwargs):
    kwargs.setdefault("page_size", 10)
    klass = _pagination_map[name]
    return type("Factory%s" % klass.__name__, (klass,), kwargs)


class DynamicFieldsMixin:
    """
    Allows creating of serializer fields selectively by passing 'fields'
    keyword argument.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed, existing = set(fields), set(self.fields)  # noqa
            for field_name in existing - allowed:
                self.fields.pop(field_name)  # noqa


class APIError(serializers.Serializer):  # noqa
    # Generic error serializer for documentation rendering.
    detail = serializers.CharField()
