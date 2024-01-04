from pathlib import Path

from django.utils.translation import gettext_lazy as _

from envanter import env

BASE_DIR = Path(__file__).resolve().parent.parent


ROOT_URLCONF = "asu.urls"
ASGI_APPLICATION = "asu.gateways.dev.application"
WSGI_APPLICATION = "asu.gateways.wsgi.application"

SECRET_KEY = env.str("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # First party apps
    "asu",
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
    "two_factor.plugins.phonenumber",
]

if DEBUG:
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {"asu": "asu.utils.templatetags"},
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
AUTH_USER_MODEL = "account.User"
SESSION_ENGINE = env.str("SESSION_ENGINE")
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")

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
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = "/code/asu/media"

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

    # Properly identify internal IP in Docker container
    import socket

    *__, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips]


CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
SECURE_PROXY_SSL_HEADER = env.list("SECURE_PROXY_SSL_HEADER", default=None)
