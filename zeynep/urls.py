import importlib

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.root_view_name = "api-root"


# Logic to scan through local apps and
# register routers & custom urlpatterns

local_apps = (
    app for app in settings.INSTALLED_APPS if app.startswith("zeynep.")
)
api_urlpatterns = []

for app in local_apps:
    module = importlib.import_module("%s.urls" % app)
    app_router = getattr(module, "router", None)
    app_urls = getattr(module, "api_urlpatterns", None)

    if app_router is not None:
        router.registry.extend(app_router.registry)

    if app_urls is not None:
        api_urlpatterns.extend(app_urls)


urlpatterns = [
    path("api/", include(router.urls + api_urlpatterns)),
    path("admin/", admin.site.urls),
]
