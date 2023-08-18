from asu.settings import *  # noqa: F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}
INSTALLED_APPS.remove("debug_toolbar")  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
