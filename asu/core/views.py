from __future__ import annotations

from typing import Any, Callable, cast

from django import urls
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import URLPattern, URLResolver
from django.views import defaults

from rest_framework.exceptions import (
    APIException,
    NotAcceptable,
    NotFound,
    PermissionDenied,
)
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import APIRootView as BaseAPIRootView
from rest_framework.views import APIView

from drf_spectacular.plumbing import get_relative_url, set_query_parameters
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import AUTHENTICATION_CLASSES
from ipware import get_client_ip

from asu.core.utils import messages
from asu.core.utils.rest import exception_handler


class APIRootView(BaseAPIRootView):
    namespaces = ("docs", "api", "oauth2_provider", "two_factor")
    permission_classes = [AllowAny]

    def resolve_url(self, namespace: str, url: URLPattern) -> str | None:
        try:
            relpath = reverse(
                namespace + ":" + str(url.name),
                kwargs=dict(url.pattern.regex.groupindex),
                request=self.request,
            )
        except urls.NoReverseMatch:
            return None
        return self.request.build_absolute_uri(relpath)

    def order(self, resolver: URLResolver | URLPattern) -> int:
        if isinstance(resolver, URLPattern):
            return len(self.namespaces)

        try:
            return self.namespaces.index(resolver.namespace)
        except ValueError:
            return len(self.namespaces)

    def get_routes(self) -> dict[str, Any]:
        url_resolver = urls.get_resolver(urls.get_urlconf())
        resolvers = url_resolver.url_patterns

        routes = {}
        for resolver in sorted(resolvers, key=self.order):
            if not isinstance(resolver, URLResolver):
                continue

            namespace = resolver.namespace
            if namespace not in self.namespaces:
                continue

            values = self.visit(resolver, namespace)
            regex = str(resolver.pattern)
            routes[regex] = values
        return routes

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ip, _ = get_client_ip(request)
        ret = {
            "version": request.version,
            "secure": request.is_secure(),
            "ip": ip,
            "user-agent": request.headers.get("user-agent"),
            "docs": request.build_absolute_uri(reverse("docs:browse")),
            "schema": request.build_absolute_uri(reverse("docs:openapi-schema")),
        }
        if settings.DEBUG or request.query_params.get("routes") == "1":
            ret["routes"] = self.get_routes()
        return Response(ret)

    def visit(
        self, resolver: URLResolver, namespace: str
    ) -> list[dict[str, Any]] | dict[str, Any]:
        values, namespaces = [], {}
        for entry in resolver.url_patterns:
            if isinstance(entry, URLResolver):
                # This is a `URLResolver`, we have to recursively check
                # for `URLPattern`s inside. While doing that, check
                # if the resolver has any namespace, if so, group
                # `URLPatterns` by namespace.
                if (sub := entry.namespace) is not None:
                    ns = "%s:%s" % (namespace, sub)
                    namespaces[sub] = self.visit(entry, ns)
                else:
                    patterns = self.visit(entry, namespace)
                    patterns = cast(list[dict[str, Any]], patterns)
                    values.extend(patterns)
            else:
                # This is a plain URLPattern, just append it to
                # the values.
                values.append(self.get_value(entry, namespace))
        # If there are any namespaces inside this resolver, return
        # a mapping that contains URLs for given namespace. Otherwise,
        # just return a list which points to root namespace.
        if namespaces:
            if values:
                # `URLPattern`s that use the root namespace are
                # grouped here (this only happens in case there
                # are namespaced & non-namespaced patterns together).
                namespaces = {"~": values, **namespaces}
            return namespaces
        return values

    def get_value(self, pattern: URLPattern, namespace: str) -> dict[str, Any]:
        value = {"name": pattern.name, "pattern": str(pattern.pattern)}
        url = self.resolve_url(namespace, pattern)
        if url is not None:
            value["url"] = url
        return value


class DocsView(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = spectacular_settings.SERVE_PERMISSIONS
    authentication_classes = AUTHENTICATION_CLASSES

    url_name = "docs:openapi-schema"
    template_name = "docs.html"

    @extend_schema(exclude=True)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(
            data={
                "title": spectacular_settings.TITLE,
                "schema_url": self.get_schema_url(request),
            },
            template_name=self.template_name,
        )

    def get_schema_url(self, request: Request) -> str:
        schema_url = get_relative_url(reverse(self.url_name, request=request))
        return set_query_parameters(
            url=schema_url,
            lang=request.GET.get("lang"),
            version=request.GET.get("version"),
        )


class GenericServerError(APIException):
    status_code = 500
    default_detail = messages.GENERIC_ERROR
    default_code = "server_error"


class GenericBadRequest(APIException):
    status_code = 400
    default_detail = messages.GENERIC_ERROR
    default_code = "invalid"


def as_json(exc: type[APIException]) -> JsonResponse:
    # To properly serialize the error, the exception
    # class must be a subclass of APIException.
    assert issubclass(exc, APIException)

    response = cast(Response, exception_handler(exc(), {}))
    return JsonResponse(
        response.data,
        status=response.status_code,
        json_dumps_params={"separators": (",", ":")},
    )


def should_return_json(request: HttpRequest) -> bool:
    if request.path.startswith("/api/"):
        return True
    negotiator = DefaultContentNegotiation()
    try:
        renderer, _ = negotiator.select_renderer(
            Request(request),
            renderers=[TemplateHTMLRenderer(), JSONRenderer()],
        )
        return isinstance(renderer, JSONRenderer)
    except NotAcceptable:
        pass
    return False


def negotiate(
    api: type[APIException], default: Callable[..., HttpResponse]
) -> Callable[..., HttpResponse]:
    def handler(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if should_return_json(request):
            return as_json(api)
        return default(request, *args, **kwargs)

    return handler


bad_request = negotiate(GenericBadRequest, defaults.bad_request)
server_error = negotiate(GenericServerError, defaults.server_error)
permission_denied = negotiate(PermissionDenied, defaults.permission_denied)
page_not_found = negotiate(NotFound, defaults.page_not_found)
