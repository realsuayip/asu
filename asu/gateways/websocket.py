import django

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Initialize Django early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django.setup(set_prefix=False)

from asu.auth.middleware import QueryAuthMiddleware  # noqa: E402
from asu.urls import websocket_urls  # noqa: E402

websocket = QueryAuthMiddleware(AllowedHostsOriginValidator(URLRouter(websocket_urls)))
application = ProtocolTypeRouter({"websocket": websocket})
