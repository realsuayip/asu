from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()


from asu.auth.middleware import QueryAuthMiddleware  # noqa: E402
from asu.urls import websocket_urls  # noqa: E402

websocket = QueryAuthMiddleware(AllowedHostsOriginValidator(URLRouter(websocket_urls)))
application = ProtocolTypeRouter({"http": django_asgi_app, "websocket": websocket})
