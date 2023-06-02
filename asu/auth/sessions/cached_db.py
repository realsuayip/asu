from django.contrib.sessions.backends.cached_db import (
    SessionStore as DjangoCachedDBStore,
)

from asu.auth.sessions.db import SessionStore as DBSessionStore

KEY_PREFIX = "asu.session_cache"


class SessionStore(DBSessionStore, DjangoCachedDBStore):
    cache_key_prefix = KEY_PREFIX
