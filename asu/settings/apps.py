from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from envanter import env

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",  # noqa: E501
    "DEFAULT_VERSION": "latest",
    "ALLOWED_VERSIONS": ["latest", "1.0"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "asu.utils.rest.exception_handler",
    "DEFAULT_METADATA_CLASS": "asu.utils.rest.EmptyMetadata",
}

OAUTH2_PROVIDER_APPLICATION_MODEL = "account.Application"
OAUTH2_PROVIDER = {
    "SCOPES": {
        "user.profile:read": _(
            "Retrieve your account, including the private information."
        ),
        "user.profile:write": _("Alter your profile and account settings."),
        "user.follow:read": _("Display your list of followers and follow requests."),
        "user.follow:write": _(
            "Follow and unfollow people on your behalf, send follow requests."
        ),
        "user.block:read": _("Display your list of blocked users"),
        "user.block:write": _("Block and unblock people on your behalf."),
    },
    "ERROR_RESPONSE_WITH_SCOPES": True,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,  # an hour
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400 * 180,  # 6 months
    "ROTATE_REFRESH_TOKEN": True,
    "PKCE_REQUIRED": True,
    "CLEAR_EXPIRED_TOKENS_BATCH_SIZE": 1000,
    "CLEAR_EXPIRED_TOKENS_BATCH_INTERVAL": 0.25,
}

_system_font = """\
-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,
sans-serif,"Apple Color Emoji","Segoe UI Emoji"
"""
_system_font_mono = """\
ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace
"""
SPECTACULAR_SETTINGS = {
    "VERSION": None,
    "TITLE": "asu API",
    "SCHEMA_PATH_PREFIX": "/api",
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
    "REDOC_UI_SETTINGS": {
        "expandResponses": "200,201",
        "downloadFileName": "asu-openapi-spec",
        "theme": {
            "typography": {
                "fontFamily": _system_font,
                "code": {"fontFamily": _system_font_mono},
                "headings": {"fontFamily": _system_font, "fontWeight": 600},
            },
        },
    },
    "OAUTH2_FLOWS": ["authorizationCode", "clientCredentials"],
    "OAUTH2_AUTHORIZATION_URL": reverse_lazy("oauth2_provider:authorize"),
    "OAUTH2_TOKEN_URL": reverse_lazy("oauth2_provider:token"),
}

REDIS_URL = env.str("REDIS_URL")
CELERY_BROKER_URL = env.str("RABBITMQ_URL")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

THUMBNAIL_REDIS_URL = REDIS_URL

# ----- Local apps -----

PROJECT_BRAND = env.str("PROJECT_BRAND")
PROJECT_SUPPORT_EMAIL = env.str("PROJECT_SUPPORT_EMAIL")


REGISTRATION_VERIFY_PERIOD = env.int("REGISTRATION_VERIFY_PERIOD")
REGISTRATION_REGISTER_PERIOD = env.int("REGISTRATION_REGISTER_PERIOD")
EMAIL_VERIFY_PERIOD = env.int("EMAIL_VERIFY_PERIOD")
PASSWORD_VERIFY_PERIOD = env.int("PASSWORD_VERIFY_PERIOD")
PASSWORD_RESET_PERIOD = env.int("PASSWORD_RESET_PERIOD")
