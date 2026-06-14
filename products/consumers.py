import json

from channels.generic.websocket import AsyncWebsocketConsumer


class MenuUpdatesConsumer(AsyncWebsocketConsumer):
    """Публичная подписка на обновления меню: ws/menu/"""

    async def connect(self):
        await self.channel_layer.group_add('menu_updates', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('menu_updates', self.channel_name)

    async def menu_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'menu.update',
                    'action': event['action'],
                    'product_id': event['product_id'],
                }
            )
        )
