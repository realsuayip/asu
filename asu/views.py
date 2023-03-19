from collections import defaultdict

from django import urls
from django.urls import URLResolver, reverse

from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView


class APIRootView(BaseAPIRootView):
    namespaces = ("docs", "api", "oauth2_provider", "two_factor")

    def _resolve_url(self, namespace, url):
        try:
            relpath = reverse(
                namespace + ":" + url.name,
                kwargs=url.pattern.regex.groupindex,
            )
        except urls.NoReverseMatch:
            return None
        return self.request.build_absolute_uri(relpath)

    def _ordered(self, resolver):
        try:
            return self.namespaces.index(resolver.namespace)
        except (ValueError, AttributeError):
            return len(self.namespaces)

    def get(self, request, *args, **kwargs):
        url_resolver = urls.get_resolver(urls.get_urlconf())
        resolvers = url_resolver.url_patterns

        routes = defaultdict(list)
        for resolver in sorted(resolvers, key=self._ordered):
            if not isinstance(resolver, URLResolver):
                continue

            namespace = resolver.namespace
            if namespace not in self.namespaces:
                continue

            values = []
            for url in resolver.url_patterns:
                name = url.name
                pattern = str(url.pattern)

                value = {"name": name, "pattern": pattern}
                url = self._resolve_url(namespace, url)
                if url is not None:
                    value["url"] = url
                values.append(value)

            regex = str(resolver.pattern)
            routes[regex] = values

        ret = {
            "status": "ok",
            "version": request.version,
            "user-agent": request.headers.get("user-agent"),
            "routes": routes,
        }
        return Response(ret)
