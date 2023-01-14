from channels.generic.websocket import AsyncJsonWebsocketConsumer

from zaida.auth.models import User


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def receive_json(self, content, **kwargs):
        ticket = content["ticket"]
        user_id, _ = User.objects.verify_ticket(
            ticket, ident="websocket", max_age=10
        )

        if getattr(self, "group", None) is None:
            self.group = "conversations_%s" % user_id  # noqa
            await self.channel_layer.group_add(self.group, self.channel_name)

    async def disconnect(self, code):
        if group := getattr(self, "group", None):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def conversation_message(self, event):
        await self.send_json(event)
