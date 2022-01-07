from django.contrib import admin
from django.urls import include, path

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.root_view_name = "api-root"


urlpatterns = [
    path("api/", include(router.urls)),
    path("admin/", admin.site.urls),
]
