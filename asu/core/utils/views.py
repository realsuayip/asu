import abc
import typing
from typing import Any, NotRequired
from uuid import UUID

from django.db.models import Model, QuerySet

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema_view
from rest_filters import FilterSet

from asu.core.utils.typing import UserRequest


class ViewSetMeta(abc.ABCMeta):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type[Any], ...],
        classdict: dict[str, Any],
    ) -> ViewSetMeta:
        cls = super().__new__(mcs, name, bases, classdict)
        schemas = classdict.get("schemas")
        if schemas is not None:
            # Get related action and decorate
            # it with extension e.g. extend_schema.
            cls = extend_schema_view(**schemas)(cls)
        return cls


class ViewSetKwargs(typing.TypedDict, total=False):
    pk: NotRequired[UUID]


class ExtendedViewSet[T: Model](viewsets.GenericViewSet[T], metaclass=ViewSetMeta):
    lookup_value_converter = "uuid"
    request: UserRequest
    kwargs: ViewSetKwargs  # type: ignore[assignment]

    schemas: dict[str, Any] | None = None
    serializer_classes: dict[str, type[serializers.BaseSerializer[Any]]] = {}
    filterset_classes: dict[str, type[FilterSet[T]]] = {}
    scopes: dict[str, list[str] | str] = {}

    def perform_action(
        self,
        serializer: serializers.BaseSerializer[Any] | None = None,
        *,
        status_code: int = status.HTTP_200_OK,
    ) -> Response:
        # Similar functionality from mixins.CreateModelMixin
        # for ViewSet actions.
        assert status.is_success(status_code)

        if serializer is None:
            serializer = self.get_serializer(data=self.request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        data = serializer.data or None
        status_code = status_code if data else status.HTTP_204_NO_CONTENT
        return Response(data, status=status_code)

    def perform_list_action(self, queryset: QuerySet[T]) -> Response:
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def get_filterset_class(self) -> type[FilterSet[T]] | None:
        return self.filterset_classes.get(self.action)

    def get_serializer_class(self) -> type[serializers.BaseSerializer[Any]]:
        serializer = self.serializer_classes.get(self.action, self.serializer_class)
        assert serializer is not None
        return serializer

    @property
    def required_scopes(self) -> list[str]:
        """
        Classify scopes depending on the request method. 'write' for
        unsafe methods and 'read' for safe methods. Used by RequireScope
        permission class.
        """

        # Reference to non-existing action, ignore scopes. Likely to
        # result in 405 Method Not Allowed.
        action = self.action
        if not action:
            return []

        spec = self.scopes[action]
        mode = "read" if self.request.method in SAFE_METHODS else "write"

        if isinstance(spec, str):
            scope = "%s:%s" % (spec, mode)
            return [scope]

        return ["%s:%s" % (scope, mode) for scope in spec]
