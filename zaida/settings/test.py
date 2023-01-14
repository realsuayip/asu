from zaida.settings import *  # noqa

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Tests are failing on 'RedisChannelLayer' due to a bug present in
# channels v4, until it is fixed, run tests on 'InMemoryChannelLayer'.
CHANNEL_LAYERS = {
    # Fixme later.
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
