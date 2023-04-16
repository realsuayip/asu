import os

from django.core.asgi import get_asgi_application
from django.urls import re_path

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from asu.messaging.websocket import ConversationConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "asu.settings")

websocket_urlpatterns = [
    re_path(r"ws/conversations/$", ConversationConsumer.as_asgi()),
]

django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
    }
)
