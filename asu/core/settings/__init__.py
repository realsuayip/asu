import sys
from pathlib import Path

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from envanter import env

BASE_DIR = Path(__file__).resolve().parents[3]
TESTING = "pytest" in sys.argv[0]

ROOT_URLCONF = "asu.core.urls"
ASGI_APPLICATION = "asu.core.gateways.dev.application"
WSGI_APPLICATION = "asu.core.gateways.wsgi.application"


SECRET_KEY = env.str("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

if TESTING:
    DEBUG = False


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # First party apps
    "asu.core",
    "asu.auth",
    "asu.verification",
    "asu.messaging",
    # Third party apps
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "channels",
    "sorl.thumbnail",
    "widget_tweaks",
    "django_celery_beat",
    "corsheaders",
    # OAuth2
    "oauth2_provider",
    # Two-factor authentication
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    "two_factor",
]

if DEBUG or TESTING:
    # Overrides `runserver` command to add WebSocket capabilities
    # in local development environment. In production, `uvicorn`
    # is used instead.
    INSTALLED_APPS.insert(0, "daphne")


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "asu.auth.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "asu.auth.middleware.UserActivityMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "HOST": env.str("DATABASE_HOST"),
        "PORT": env.str("DATABASE_PORT"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.str("REDIS_URL"),
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {"asu": "asu.core.utils.templatetags"},
        },
    },
]


password_validators = [
    "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    "django.contrib.auth.password_validation.MinimumLengthValidator",
    "django.contrib.auth.password_validation.CommonPasswordValidator",
    "django.contrib.auth.password_validation.NumericPasswordValidator",
]
AUTH_PASSWORD_VALIDATORS = [{"NAME": validator} for validator in password_validators]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_USER_MODEL = "account.User"
SESSION_ENGINE = env.str("SESSION_ENGINE")
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")

LOCALE_PATHS = [BASE_DIR / "asu/core/locale"]
LANGUAGES = [
    ("en", _("English")),
    ("tr", _("Turkish")),
]
LANGUAGE_CODE = env.str("DJANGO_LANGUAGE_CODE")
LANGUAGE_COOKIE_NAME = "language"
TIME_ZONE = env.str("DJANGO_TIME_ZONE")
USE_I18N = True
USE_TZ = True

STORAGES = {
    "default": {"BACKEND": env.str("DEFAULT_FILE_STORAGE")},
    "staticfiles": {"BACKEND": env.str("STATICFILES_STORAGE")},
}

STATIC_URL = "static/"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env.str("EMAIL_BACKEND")
EMAIL_HOST = env.str("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")

LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "two_factor:profile"

if DEBUG:
    # Django debug toolbar related configuration
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")


CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
SECURE_PROXY_SSL_HEADER = env.list("SECURE_PROXY_SSL_HEADER", default=None)


# -------------------------------THIRD PARTY APPS------------------------------


DEFAULT_RENDERER_CLASSES = ["rest_framework.renderers.JSONRenderer"]
DEFAULT_AUTHENTICATION_CLASSES = [
    "oauth2_provider.contrib.rest_framework.OAuth2Authentication"
]
URL_FORMAT_OVERRIDE = None


if DEBUG and not TESTING:
    DEFAULT_RENDERER_CLASSES = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
    DEFAULT_AUTHENTICATION_CLASSES = [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ]
    URL_FORMAT_OVERRIDE = "format"


REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_VERSION": env.str("API_DEFAULT_VERSION"),
    "ALLOWED_VERSIONS": env.list("API_ALLOWED_VERSIONS"),
    "DEFAULT_AUTHENTICATION_CLASSES": DEFAULT_AUTHENTICATION_CLASSES,
    "DEFAULT_PERMISSION_CLASSES": ["asu.core.utils.denier.DenyAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "asu.core.utils.rest.exception_handler",
    "DEFAULT_METADATA_CLASS": "asu.core.utils.rest.EmptyMetadata",
    "DEFAULT_RENDERER_CLASSES": DEFAULT_RENDERER_CLASSES,
    "URL_FORMAT_OVERRIDE": URL_FORMAT_OVERRIDE,
}

OAUTH2_PROVIDER_APPLICATION_MODEL = "account.Application"
OAUTH2_PROVIDER = {
    "SCOPES": {
        "user.profile:read": _("Retrieve your account, with your public information."),
        "user.profile.email:read": _("Retrieve your email address."),
        "user.profile.private:read": _(
            "Retrieve your private information, including your personal preferences."
        ),
        "user.profile:write": _(
            "Alter your profile and account settings,"
            " including your personal preferences."
        ),
        "user.follow:read": _("Display your list of followers and follow requests."),
        "user.follow:write": _(
            "Follow and unfollow people on your behalf, send follow requests."
        ),
        "user.block:read": _("Display your list of blocked users"),
        "user.block:write": _("Block and unblock people on your behalf."),
    },
    "ERROR_RESPONSE_WITH_SCOPES": False,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,  # an hour
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400 * 180,  # 6 months
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,
    "PKCE_REQUIRED": True,
    "CLEAR_EXPIRED_TOKENS_BATCH_SIZE": 1000,
    "CLEAR_EXPIRED_TOKENS_BATCH_INTERVAL": 0.25,
}

# A custom mapping that defines which scopes are required to display certain
# user fields. This allows fine-grained access to user information.
OAUTH2_USER_FIELDS = {
    "user.profile:read": {
        "id",
        "display_name",
        "username",
        "description",
        "website",
        "profile_picture",
        "date_joined",
        "is_private",
    },
    "user.profile.email:read": {"email"},
    "user.profile.private:read": {
        "gender",
        "language",
        "birth_date",
        "allows_receipts",
        "allows_all_messages",
        "two_factor_enabled",
    },
}

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
THUMBNAIL_FORCE_OVERWRITE = True

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME")

SENTRY_ENABLED = env.bool("SENTRY_ENABLED")
SENTRY_DSN = env.str("SENTRY_DSN")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE")


# ----------------------------------LOCAL APPS---------------------------------


PROJECT_BRAND = env.str("PROJECT_BRAND")
PROJECT_ENVIRONMENT = env.choice(
    "PROJECT_ENVIRONMENT", choices=("dev", "stage", "production")
)
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
