from pathlib import Path

from envanter import env

BASE_DIR = Path(__file__).resolve().parent.parent


ROOT_URLCONF = "asu.urls"
ASGI_APPLICATION = "asu.gateways.dev.application"
WSGI_APPLICATION = "asu.wsgi.application"

SECRET_KEY = env.str("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


INSTALLED_APPS = [
    "daphne",
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
    # OAuth2
    "oauth2_provider",
    # Two-factor authentication
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    "two_factor",
    "two_factor.plugins.phonenumber",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "asu.auth.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
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

LANGUAGE_CODE = env.str("DJANGO_LANGUAGE_CODE")
TIME_ZONE = env.str("DJANGO_TIME_ZONE")

USE_I18N = True
USE_TZ = True


# TODO: Switch to 4.2 `STORAGES` setting once all
#  dependencies support using it.
DEFAULT_FILE_STORAGE = env.str("DEFAULT_FILE_STORAGE")
STATICFILES_STORAGE = env.str("STATICFILES_STORAGE")

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


LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "two_factor:profile"

if DEBUG:
    # Django debug toolbar related configuration
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

    # Properly identify internal IP in Docker container
    import socket

    *_, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips]
