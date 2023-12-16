import typing
from collections.abc import Callable

from django.core import signing
from django.http import HttpRequest, HttpResponse, QueryDict

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.security.websocket import WebsocketDenier

from asu.auth.models import User


class UserActivityMiddleware:
    def __init__(self, get_response: Callable[..., HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user

        if user.is_authenticated and user.is_frozen:
            user.reactivate()

        return self.get_response(request)


class QueryAuthMiddleware:
    """
    Authenticate using `ticket` query parameter. This short-living, signed
    ticket is obtained via the API `api:auth:user-ticket`.

    Connection is denied if the ticket could not be verified. All consumers
    require this authentication.
    """

    def __init__(self, app: AsyncWebsocketConsumer) -> None:
        self.app = app

    @typing.no_type_check
    async def __call__(self, scope, receive, send):
        query = QueryDict(scope["query_string"])
        ticket = query.get("ticket", "")
        try:
            user_id, uuid = User.objects.verify_ticket(
                ticket, ident="websocket", max_age=10
            )
            scope["user_id"] = user_id
            scope["user_uuid"] = uuid
        except signing.BadSignature:
            denier = WebsocketDenier()
            return await denier(scope, receive, send)
        return await self.app(scope, receive, send)
