from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from asu.auth.models import User


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def receive_json(
        self, content: dict[str, Any], **kwargs: Any
    ) -> None:
        ticket = content["ticket"]
        user_id, _ = User.objects.verify_ticket(
            ticket, ident="websocket", max_age=10
        )

        if getattr(self, "group", None) is None:
            self.group = "conversations_%s" % user_id
            await self.channel_layer.group_add(self.group, self.channel_name)

    async def disconnect(self, code: str) -> None:
        if group := getattr(self, "group", None):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def conversation_message(self, event: str) -> None:
        await self.send_json(event)
