from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from asu.messaging.models.message import MessageEvent


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    def get_group(self) -> str:
        return "conversations_%s" % self.scope["user_id"]

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.get_group(), self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(self.get_group(), self.channel_name)

    async def conversation_message(self, event: MessageEvent) -> None:
        await self.send_json(event)

    async def websocket_receive(self, message: dict[str, Any]) -> None:
        # Deny incoming frames.
        await self.close()
