from __future__ import annotations

from typing import Any, cast

from django import urls
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import URLPattern, URLResolver, reverse
from django.utils.translation import gettext
from django.views import defaults

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView

from django_stubs_ext import StrOrPromise
from ipware import get_client_ip

from asu.utils import messages


class APIRootView(BaseAPIRootView):
    namespaces = ("docs", "api", "oauth2_provider", "two_factor")

    def resolve_url(self, namespace: str, url: URLPattern) -> str | None:
        try:
            relpath = reverse(
                namespace + ":" + str(url.name),
                kwargs=dict(url.pattern.regex.groupindex),
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

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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

        ip, _ = get_client_ip(request)
        ret = {
            "status": "ok",
            "version": request.version,
            "user-agent": request.headers.get("user-agent"),
            "ip": ip,
            "routes": routes,
        }
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


def as_json(message: StrOrPromise, /, *, status: int) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def should_return_json(request: HttpRequest) -> bool:
    return (
        request.path.startswith("/api/") or request.content_type == "application/json"
    )


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    if should_return_json(request):
        return as_json(messages.GENERIC_ERROR, status=400)
    return defaults.bad_request(request, exception)


def server_error(request: HttpRequest) -> HttpResponse:
    if should_return_json(request):
        return as_json(messages.GENERIC_ERROR, status=500)
    return defaults.server_error(request)


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    if should_return_json(request):
        return as_json(
            gettext("You do not have permission to perform this action."),
            status=403,
        )
    return defaults.permission_denied(request, exception)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    if should_return_json(request):
        return as_json(gettext("Not found."), status=404)
    return defaults.page_not_found(request, exception)
