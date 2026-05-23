from asu.core.settings import *  # noqa: F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}
CELERY_TASK_ALWAYS_EAGER = True

PROJECT_ENVIRONMENT = "production"
