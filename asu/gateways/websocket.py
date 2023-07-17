import django

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Initialize Django early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django.setup(set_prefix=False)

from asu.urls import websocket_urls  # noqa: E402

application = ProtocolTypeRouter(
    {"websocket": AllowedHostsOriginValidator(URLRouter(websocket_urls))}
)
