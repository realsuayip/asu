from asu.utils.envparse import env

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",  # noqa
    "DEFAULT_VERSION": "latest",
    "ALLOWED_VERSIONS": ["latest", "1.0"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "asu.utils.rest.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "VERSION": None,
    "TITLE": "asu API",
}

REDIS_URL = "redis://redis:6379/1"
CELERY_BROKER_URL = "amqp://guest:guest@rabbitmq:5672/"

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

REGISTRATION_VERIFY_PERIOD = env.int("REGISTRATION_VERIFY_PERIOD", 600)
REGISTRATION_REGISTER_PERIOD = env.int("REGISTRATION_REGISTER_PERIOD", 600)

EMAIL_VERIFY_PERIOD = env.int("EMAIL_VERIFY_PERIOD", 600)

PASSWORD_VERIFY_PERIOD = env.int("PASSWORD_VERIFY_PERIOD", 600)
PASSWORD_RESET_PERIOD = env.int("PASSWORD_RESET_PERIOD", 600)
