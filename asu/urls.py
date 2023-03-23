from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from oauth2_provider.urls import base_urlpatterns as oauth_urls
from two_factor import views as tf

from asu.views import (
    APIRootView,
    bad_request,
    page_not_found,
    permission_denied,
    server_error,
)

api_urls = [
    path("", APIRootView.as_view(), name="api-root"),
    path("", include("asu.auth.urls")),
    path("", include("asu.verification.urls")),
    path("", include("asu.messaging.urls")),
]

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
    path("api/", include((api_urls, "api"))),
    path("o/", include((oauth_urls, "oauth2_provider"))),
    path("docs/", include((docs_urls, "docs"))),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))


handler400 = bad_request
handler403 = permission_denied
handler404 = page_not_found
handler500 = server_error
