from collections import defaultdict

from django import urls
from django.http import JsonResponse
from django.urls import URLResolver, reverse
from django.utils.translation import gettext
from django.views import defaults

from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView

from asu.utils import messages


class APIRootView(BaseAPIRootView):
    namespaces = ("docs", "api", "oauth2_provider", "two_factor")

    def resolve_url(self, namespace, url):
        try:
            relpath = reverse(
                namespace + ":" + url.name,
                kwargs=url.pattern.regex.groupindex,
            )
        except urls.NoReverseMatch:
            return None
        return self.request.build_absolute_uri(relpath)

    def order(self, resolver):
        try:
            return self.namespaces.index(resolver.namespace)
        except (ValueError, AttributeError):
            return len(self.namespaces)

    def get(self, request, *args, **kwargs):
        url_resolver = urls.get_resolver(urls.get_urlconf())
        resolvers = url_resolver.url_patterns

        routes = defaultdict(list)
        for resolver in sorted(resolvers, key=self.order):
            if not isinstance(resolver, URLResolver):
                continue

            namespace = resolver.namespace
            if namespace not in self.namespaces:
                continue

            values = self.visit(resolver, namespace)
            regex = str(resolver.pattern)
            routes[regex] = values

        ret = {
            "status": "ok",
            "version": request.version,
            "user-agent": request.headers.get("user-agent"),
            "routes": routes,
        }
        return Response(ret)

    def visit(self, resolver, namespace):
        values = []
        for entry in resolver.url_patterns:
            if isinstance(entry, URLResolver):
                values.extend(self.visit(entry, namespace))
            else:
                values.append(self.get_value(entry, namespace))
        return values

    def get_value(self, url, namespace):
        value = {"name": url.name, "pattern": str(url.pattern)}
        url = self.resolve_url(namespace, url)
        if url is not None:
            value["url"] = url
        return value


def as_json(message, /, *, status):
    return JsonResponse({"detail": message}, status=status)


def should_return_json(request) -> bool:
    return (
        request.path.startswith("/api/")
        or request.content_type == "application/json"
    )


def bad_request(request, exception):
    if should_return_json(request):
        return as_json(messages.GENERIC_ERROR, status=400)
    return defaults.bad_request(request, exception)


def server_error(request):
    if should_return_json(request):
        return as_json(messages.GENERIC_ERROR, status=500)
    return defaults.server_error(request)


def permission_denied(request, exception):
    if should_return_json(request):
        return as_json(
            gettext("You do not have permission to perform this action."),
            status=403,
        )
    return defaults.permission_denied(request, exception)


def page_not_found(request, exception):
    if should_return_json(request):
        return as_json(gettext("Not found."), status=404)
    return defaults.page_not_found(request, exception)
