from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from envanter import env

DEBUG = env.bool("DJANGO_DEBUG")

DEFAULT_RENDERER_CLASSES = ["rest_framework.renderers.JSONRenderer"]
DEFAULT_AUTHENTICATION_CLASSES = [
    "oauth2_provider.contrib.rest_framework.OAuth2Authentication"
]
if DEBUG:
    DEFAULT_RENDERER_CLASSES = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
    DEFAULT_AUTHENTICATION_CLASSES = [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ]


REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_VERSION": env.str("API_DEFAULT_VERSION"),
    "ALLOWED_VERSIONS": env.list("API_ALLOWED_VERSIONS"),
    "DEFAULT_AUTHENTICATION_CLASSES": DEFAULT_AUTHENTICATION_CLASSES,
    "DEFAULT_SCHEMA_CLASS": "asu.utils.openapi.CustomAutoSchema",
    "EXCEPTION_HANDLER": "asu.utils.rest.exception_handler",
    "DEFAULT_METADATA_CLASS": "asu.utils.rest.EmptyMetadata",
    "DEFAULT_RENDERER_CLASSES": DEFAULT_RENDERER_CLASSES,
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
    "DESCRIPTION": "Welcome to asu OpenAPI documentation. Select an endpoint"
    " from the sidebar to start.",
    "SCHEMA_PATH_PREFIX": "/api",
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
    "OAUTH2_FLOWS": ["authorizationCode", "clientCredentials"],
    "OAUTH2_AUTHORIZATION_URL": reverse_lazy("oauth2_provider:authorize"),
    "OAUTH2_TOKEN_URL": reverse_lazy("oauth2_provider:token"),
}

REDIS_URL = env.str("REDIS_URL")
CELERY_BROKER_URL = env.str("RABBITMQ_URL")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

THUMBNAIL_REDIS_URL = REDIS_URL

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME")

THUMBNAIL_FORCE_OVERWRITE = True

# ----- Local apps -----

PROJECT_BRAND = env.str("PROJECT_BRAND")
PROJECT_SUPPORT_EMAIL = env.str("PROJECT_SUPPORT_EMAIL")
PROJECT_URL_ACCOUNT_CREATION = env.str("PROJECT_URL_ACCOUNT_CREATION")
PROJECT_URL_PASSWORD_RESET = env.str("PROJECT_URL_PASSWORD_RESET")
PROJECT_URL_TERMS = env.str("PROJECT_URL_TERMS")
PROJECT_URL_PRIVACY = env.str("PROJECT_URL_PRIVACY")
PROJECT_URL_SECURITY = env.str("PROJECT_URL_SECURITY")
PROJECT_URL_CONTACT = env.str("PROJECT_URL_CONTACT")


REGISTRATION_VERIFY_PERIOD = env.int("REGISTRATION_VERIFY_PERIOD")
REGISTRATION_REGISTER_PERIOD = env.int("REGISTRATION_REGISTER_PERIOD")
EMAIL_VERIFY_PERIOD = env.int("EMAIL_VERIFY_PERIOD")
PASSWORD_VERIFY_PERIOD = env.int("PASSWORD_VERIFY_PERIOD")
PASSWORD_RESET_PERIOD = env.int("PASSWORD_RESET_PERIOD")
