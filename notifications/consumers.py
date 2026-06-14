import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket для real-time уведомлений (колокольчик).
    Пользователь подключается — получает новые уведомления мгновенно.
    Транспорт: Redis Channel Layer.
    """

    async def connect(self):
        user = self.scope['user']
        if isinstance(user, AnonymousUser) or user.is_anonymous:
            await self.close()
            return

        self.group_name = f'notifications_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def new_notification(self, event):
        """Новое уведомление → отправить клиенту."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event.get('id'),
            'notification_type': event.get('notification_type'),
            'title': event.get('title'),
            'link': event.get('link', ''),
            'created_at': event.get('created_at', ''),
        }))
