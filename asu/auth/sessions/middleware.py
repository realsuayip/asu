from django.conf import settings
from django.contrib.sessions.middleware import (
    SessionMiddleware as DjangoSessionMiddleware,
)
from django.http import HttpRequest

from ipware import get_client_ip

from asu.auth.sessions.db import SessionStore


class SessionMiddleware(DjangoSessionMiddleware):
    SessionStore: type[SessionStore]

    def process_request(self, request: HttpRequest) -> None:
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

        user_agent = request.headers.get("user-agent") or ""
        ip, _ = get_client_ip(request)

        request.session = self.SessionStore(
            session_key=session_key,
            user_agent=user_agent,
            ip=ip,
        )
