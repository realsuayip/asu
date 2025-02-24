import typing

import django
from django.core.handlers.asgi import ASGIHandler
from django.template.response import SimpleTemplateResponse

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Initialize Django early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django.setup(set_prefix=False)

from asu.auth.middleware import QueryAuthMiddleware  # noqa: E402
from asu.urls import websocket_urls  # noqa: E402


@typing.no_type_check
async def http(scope, receive, send):
    # A simple http handler to properly deny non-websocket requests.
    handler = ASGIHandler()
    response = SimpleTemplateResponse("400.html", status=400)
    response.render()
    await handler.send_response(response, send)


websocket = QueryAuthMiddleware(AllowedHostsOriginValidator(URLRouter(websocket_urls)))
application = ProtocolTypeRouter({"http": http, "websocket": websocket})
