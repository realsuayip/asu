from __future__ import annotations

import abc
from typing import Any, TypeVar

from django.db import models

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema_view

from asu.core.utils.typing import UserRequest

MT_co = TypeVar("MT_co", bound=models.Model, covariant=True)


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


class ExtendedViewSet(viewsets.GenericViewSet[MT_co], metaclass=ViewSetMeta):
    schemas: dict[str, Any] | None = None
    serializer_classes: dict[str, type[serializers.BaseSerializer[Any]]] = {}
    filterset_classes: dict[str, type[filters.FilterSet]] = {}
    scopes: dict[str, list[str] | str] = {}
    request: UserRequest

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

    @property
    def filterset_class(self) -> type[filters.FilterSet] | None:
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
