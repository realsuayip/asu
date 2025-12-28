import abc
from collections.abc import Callable, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NotRequired,
    ReadOnly,
    TypedDict,
    TypeIs,
    cast,
    get_args,
)
from uuid import UUID

from django.db.models import Model, QuerySet
from django.http import HttpResponseBase

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action as viewset_action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema_view
from rest_filters import FilterSet

from asu.core.utils.typing import UserRequest

if TYPE_CHECKING:
    from rest_framework.decorators import ViewSetAction
    from rest_framework.permissions import _PermissionClass, _SupportsHasPermission


ViewSetMixinAction = Literal[
    "list",
    "retrieve",
    "create",
    "update",
    "partial_update",
    "destroy",
]


def is_mixin_action(value: str) -> TypeIs[ViewSetMixinAction]:
    return value in get_args(ViewSetMixinAction)


class MixinActionDict[T](TypedDict):
    list: NotRequired[ReadOnly[T]]
    retrieve: NotRequired[ReadOnly[T]]
    create: NotRequired[ReadOnly[T]]
    update: NotRequired[ReadOnly[T]]
    partial_update: NotRequired[ReadOnly[T]]
    destroy: NotRequired[ReadOnly[T]]


class ViewSetKwargs(TypedDict, total=False):
    pk: NotRequired[ReadOnly[UUID]]


class ViewSetMeta(abc.ABCMeta):
    @staticmethod
    def check(classdict: dict[str, Any]) -> None:
        replacements = (
            ("serializer_class", "serializer_classes"),
            ("filterset_class", "filterset_classes"),
        )
        for orig, repl in replacements:
            assert classdict.get(orig) is None, f"use `{repl}` instead"

        mixin_attrs = (
            "serializer_classes",
            "filterset_classes",
            "permission_classes",
            "required_scopes",
        )
        for attr in mixin_attrs:
            value = classdict.get(attr, {})
            assert isinstance(value, dict), f"{attr} must be a dict"
            for name in value:
                assert is_mixin_action(name), f"action '{name}' is not a mixin action"

    def __new__(
        mcs,
        name: str,
        bases: tuple[type[Any], ...],
        classdict: dict[str, Any],
    ) -> ViewSetMeta:
        mcs.check(classdict)
        cls = super().__new__(mcs, name, bases, classdict)
        schemas = classdict.get("schemas")
        if schemas is not None:
            # Get related action and decorate
            # it with extension e.g. extend_schema.
            cls = extend_schema_view(**schemas)(cls)
        return cls


class ExtendedViewSet[T: Model](viewsets.GenericViewSet[T], metaclass=ViewSetMeta):
    lookup_value_converter = "uuid"
    request: UserRequest
    kwargs: ViewSetKwargs  # type: ignore[assignment]

    schemas: dict[str, Any] | None = None
    serializer_classes: MixinActionDict[type[serializers.BaseSerializer[Any]]] = {}
    filterset_classes: MixinActionDict[type[FilterSet[T]]] = {}
    required_scopes: MixinActionDict[list[str]] = {}
    permission_classes: Mapping[str, Sequence[_PermissionClass]] = {}  # type: ignore[assignment]

    # Set `filterset_class` so that non-mixin actions can override this.
    filterset_class = None

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
        if is_mixin_action(self.action):
            return self.filterset_classes.get(self.action)
        return getattr(self, "filterset_class", None)

    def get_serializer_class(self) -> type[serializers.BaseSerializer[Any]]:
        # If action is mixin-based, `serializer_classes` must be used. Regular
        # actions (using `@action` decorator) should supply `serializer_class`.
        if is_mixin_action(self.action):
            klass = self.serializer_classes.get(self.action)
        else:
            klass = self.serializer_class
        assert klass, f"missing serializer for action {self.action}"
        return klass

    def get_required_scopes(self) -> list[str]:
        mode = "read" if self.request.method in SAFE_METHODS else "write"
        if is_mixin_action(self.action):
            scopes = self.required_scopes[self.action]
        else:
            scopes = cast("list[str]", self.required_scopes)
        assert scopes, f"missing scopes for action '{self.action}'"
        assert isinstance(scopes, list), f"invalid scopes for action '{self.action}'"
        return ["%s:%s" % (scope, mode) for scope in scopes]

    def get_permissions(self) -> Sequence[_SupportsHasPermission]:
        if is_mixin_action(self.action):
            klasses = self.permission_classes[self.action]
            return [klass() for klass in klasses]
        return super().get_permissions()


def action[RT: HttpResponseBase, **P](
    *,
    methods: list[Literal["get", "post", "put", "patch", "delete"]],
    detail: bool,
    url_path: str | None = None,
    url_name: str | None = None,
    permission_classes: Sequence[_PermissionClass],
    serializer_class: type[serializers.BaseSerializer[Any]] | None = None,
    filterset_class: type[FilterSet[Model]] | None = None,
    required_scopes: list[str] | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, RT]], ViewSetAction[Callable[P, RT]]]:
    return viewset_action(
        methods=methods,
        detail=detail,
        url_path=url_path,
        url_name=url_name,
        permission_classes=permission_classes,
        serializer_class=serializer_class,
        filterset_class=filterset_class,
        required_scopes=required_scopes,
        **kwargs,
    )
