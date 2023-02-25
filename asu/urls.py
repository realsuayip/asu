import importlib
from collections import defaultdict

from django import urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLResolver, include, path, reverse

from rest_framework.response import Response
from rest_framework.routers import APIRootView, DefaultRouter

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from oauth2_provider.urls import base_urlpatterns as oauth_urls
from two_factor import views as tf


class APIRoot(APIRootView):
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


class APIRouter(DefaultRouter):
    include_format_suffixes = False
    APIRootView = APIRoot


router = APIRouter()
router.root_view_name = "api-root"

# Logic to scan through local apps and
# register routers & custom urlpatterns

api_urls = []
local_apps = (app for app in settings.INSTALLED_APPS if app.startswith("asu."))
for app in local_apps:
    try:
        module = importlib.import_module("%s.urls" % app)
    except ModuleNotFoundError:
        continue

    app_router = getattr(module, "router", None)
    app_urls = getattr(module, "api_urlpatterns", None)

    if app_router is not None:
        router.registry.extend(app_router.registry)

    if app_urls is not None:
        api_urls.extend(app_urls)


docs_urls = [
    path("schema/", SpectacularAPIView.as_view(), name="openapi-schema"),
    path(
        "",
        SpectacularRedocView.as_view(url_name="docs:openapi-schema"),
        name="browse",
    ),
]

account_urls = [
    path("", tf.ProfileView.as_view(), name="profile"),
    path("login/", tf.LoginView.as_view(), name="login"),
    path("two-factor/setup/", tf.SetupView.as_view(), name="setup"),
    path("two-factor/qrcode/", tf.QRGeneratorView.as_view(), name="qr"),
    path(
        "two-factor/setup/complete/",
        tf.SetupCompleteView.as_view(),
        name="setup_complete",
    ),
    path(
        "two-factor/backup/tokens/",
        tf.BackupTokensView.as_view(),
        name="backup_tokens",
    ),
    path("two-factor/disable/", tf.DisableView.as_view(), name="disable"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include((account_urls, "two_factor"))),
    path("api/", include((router.urls + api_urls, "api"))),
    path("o/", include((oauth_urls, "oauth2_provider"))),
    path("docs/", include((docs_urls, "docs"))),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
