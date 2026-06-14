import logging

from celery import shared_task
from django.core.cache import cache

from analytics.models import AnalyticsEvent

logger = logging.getLogger(__name__)

UNREAD_COUNT_KEY = 'chat:unread:{room_id}:{user_id}'
UNREAD_TTL = 600


@shared_task
def process_chat_message(room_id, sender_id, text):
    """
    Асинхронная обработка сообщения чата.
    RabbitMQ → Celery → Redis (счётчики) + PostgreSQL (лог) + WebSocket (bell-уведомление).
    """
    from chat.models import ChatRoom

    try:
        room = ChatRoom.objects.select_related('user', 'moderator').get(id=room_id)
    except ChatRoom.DoesNotExist:
        return

    # Определяем получателя.
    if sender_id == room.user_id:
        recipient_id = room.moderator_id
        sender_name = room.user.username
    else:
        recipient_id = room.user_id
        sender_name = room.moderator.username if room.moderator else '—'

    # Обновляем счётчик непрочитанных чата в Redis.
    if recipient_id:
        unread_key = UNREAD_COUNT_KEY.format(room_id=room_id, user_id=recipient_id)
        try:
            # Атомарный инкремент (Redis INCR) вместо get+set: при параллельных
            # сообщениях не теряем увеличения счётчика.
            cache.incr(unread_key)
            cache.touch(unread_key, UNREAD_TTL)
        except ValueError:
            # Ключа ещё нет — создаём со счётчиком 1.
            cache.set(unread_key, 1, UNREAD_TTL)
        except Exception:
            pass

    # Bell-уведомление получателю через RabbitMQ → Celery → Redis → WebSocket.
    if recipient_id and recipient_id != sender_id:
        from notifications.tasks import notify_chat_message
        notify_chat_message.delay(recipient_id, room_id, sender_name, text[:100])

    # Лог в аналитику (PostgreSQL).
    AnalyticsEvent.objects.create(
        event_type='chat_message',
        payload={'room_id': room_id, 'sender_id': sender_id, 'text_length': len(text)},
        user_id=sender_id,
    )

    logger.info(f"[CHAT] Message processed: room={room_id}, sender={sender_id}")


@shared_task
def mark_messages_read(room_id, user_id):
    from chat.models import ChatMessage
    ChatMessage.objects.filter(room_id=room_id, is_read=False).exclude(sender_id=user_id).update(is_read=True)
    cache.delete(UNREAD_COUNT_KEY.format(room_id=room_id, user_id=user_id))
