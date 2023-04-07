from asu.settings import *  # noqa: F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
INSTALLED_APPS.remove("debug_toolbar")  # noqa: F405
