import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket-потребитель для чата.
    Сообщения доставляются в реальном времени через Redis Channel Layer.
    Сохранение в БД + асинхронное логирование через Celery/RabbitMQ.
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'chat_{self.room_id}'
        user = self.scope['user']

        if isinstance(user, AnonymousUser) or user.is_anonymous:
            await self.close()
            return

        # Проверяем, что пользователь имеет доступ к этому чату.
        has_access = await self._check_access(user.id, self.room_id)
        if not has_access:
            await self.close()
            return

        # Присоединяемся к группе чата (Redis Channel Layer).
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Отправляем историю последних сообщений.
        history = await self._get_history(self.room_id)
        await self.send(text_data=json.dumps({
            'type': 'chat.history',
            'messages': history,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Получение сообщения от клиента → сохранение → рассылка."""
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        text = data.get('text', '').strip()
        if not text:
            return

        user = self.scope['user']

        # Сохраняем сообщение в PostgreSQL.
        message = await self._save_message(self.room_id, user.id, text)

        # Рассылаем сообщение всем участникам через Redis Channel Layer.
        await self.channel_layer.group_send(self.group_name, {
            'type': 'chat.message',
            'id': message['id'],
            'sender_id': user.id,
            'sender_name': user.username,
            'text': text,
            'created_at': message['created_at'],
        })

        # Асинхронно через RabbitMQ → Celery: логирование + обновление счётчиков.
        await self._trigger_async_tasks(self.room_id, user.id, text)

    async def chat_message(self, event):
        """Отправка сообщения подключённому клиенту."""
        await self.send(text_data=json.dumps({
            'type': 'chat.message',
            'id': event['id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'text': event['text'],
            'created_at': event['created_at'],
        }))

    # ── DB-операции ──

    @database_sync_to_async
    def _check_access(self, user_id, room_id):
        from .models import ChatRoom
        from users.permissions import user_is_staff
        from django.contrib.auth.models import User

        try:
            room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return False

        # Пользователь — владелец чата.
        if room.user_id == user_id:
            return True

        # Модератор или админ — имеет доступ к любому чату.
        user = User.objects.get(id=user_id)
        if user_is_staff(user):
            # Если модератор ещё не назначен — назначаем текущего.
            if room.moderator is None:
                room.moderator = user
                room.save(update_fields=['moderator'])
            return True

        return False

    @database_sync_to_async
    def _save_message(self, room_id, sender_id, text):
        from .models import ChatMessage, ChatRoom

        msg = ChatMessage.objects.create(
            room_id=room_id,
            sender_id=sender_id,
            text=text,
        )
        # Обновляем updated_at комнаты для сортировки.
        ChatRoom.objects.filter(id=room_id).update(updated_at=msg.created_at)

        return {
            'id': msg.id,
            'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
        }

    @database_sync_to_async
    def _get_history(self, room_id, limit=50):
        from .models import ChatMessage

        messages = (
            ChatMessage.objects
            .filter(room_id=room_id)
            .select_related('sender')
            .order_by('-created_at')[:limit]
        )
        result = [
            {
                'id': m.id,
                'sender_id': m.sender_id,
                'sender_name': m.sender.username,
                'text': m.text,
                'created_at': m.created_at.strftime('%d.%m.%Y %H:%M'),
            }
            for m in reversed(messages)
        ]
        return result

    @database_sync_to_async
    def _trigger_async_tasks(self, room_id, sender_id, text):
        from .tasks import process_chat_message
        process_chat_message.delay(room_id, sender_id, text)
