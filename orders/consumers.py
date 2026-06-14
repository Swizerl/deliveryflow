import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import Order


class OrderStatusConsumer(AsyncWebsocketConsumer):
    """Подписка на статус одного заказа: ws/orders/<order_id>/"""

    async def connect(self):
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.group_name = f"order_{self.order_id}"
        user = self.scope["user"]

        if isinstance(user, AnonymousUser) or user.is_anonymous:
            await self.close()
            return

        owns_order = await self._user_owns_order(user.id, self.order_id)
        if not owns_order:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        order = await self._get_order(self.order_id)
        if order:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "order.status",
                        "order_id": order.id,
                        "status": order.status,
                    }
                )
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "order.status",
                    "order_id": event["order_id"],
                    "status": event["status"],
                }
            )
        )

    @database_sync_to_async
    def _user_owns_order(self, user_id, order_id):
        return Order.objects.filter(id=order_id, user_id=user_id).exists()

    @database_sync_to_async
    def _get_order(self, order_id):
        return Order.objects.filter(id=order_id).first()


class UserOrdersConsumer(AsyncWebsocketConsumer):
    """Все заказы пользователя: ws/orders/"""

    async def connect(self):
        user = self.scope["user"]
        if isinstance(user, AnonymousUser) or user.is_anonymous:
            await self.close()
            return

        self.group_name = f"user_orders_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "order.status",
                    "order_id": event["order_id"],
                    "status": event["status"],
                }
            )
        )
