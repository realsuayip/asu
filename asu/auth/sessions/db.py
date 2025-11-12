from typing import Any, cast

from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession

from asu.auth.models import Session


class SessionStore(DBStore):
    def __init__(
        self,
        session_key: str | None = None,
        user_agent: str = "",
        ip: str | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.ip = ip
        super().__init__(session_key)

    @classmethod
    def get_model_class(cls) -> type[AbstractBaseSession]:
        return Session

    def create_model_instance(self, data: dict[str, Any]) -> Session:
        try:
            user = int(cast("str", data.get("_auth_user_id")))
        except (ValueError, TypeError):
            user = None

        return Session(
            session_key=self._get_or_create_session_key(),  # type: ignore[attr-defined]
            session_data=self.encode(data),
            expire_date=self.get_expiry_date(),
            user=user,
            user_agent=self.user_agent,
            ip=self.ip,
        )
