import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.cache import cache

logger = logging.getLogger(__name__)

UNREAD_KEY = 'notif:unread:{user_id}'
UNREAD_TTL = 600


def get_unread_count(user_id):
    """Получить кол-во непрочитанных из Redis-кэша (или из БД)."""
    key = UNREAD_KEY.format(user_id=user_id)
    count = cache.get(key)
    if count is not None:
        return count
    from .models import Notification
    count = Notification.objects.filter(user_id=user_id, is_read=False).count()
    cache.set(key, count, UNREAD_TTL)
    return count


def invalidate_unread(user_id):
    """Сбросить Redis-кэш счётчика."""
    cache.delete(UNREAD_KEY.format(user_id=user_id))


def _push_notification_ws(user_id, notif_data):
    """Отправить уведомление в WebSocket через Redis Channel Layer."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'new.notification',
                **notif_data,
            },
        )
    except Exception as exc:
        logger.warning(f"[NOTIF] WS push failed for user {user_id}: {exc}")


@shared_task
def notify_order_status(user_id, order_id, status):
    """
    Уведомление пользователя о смене статуса заказа.
    RabbitMQ → Celery → PostgreSQL + Redis + WebSocket.
    """
    from .models import Notification

    status_labels = {
        'created': 'создан',
        'processing': 'обрабатывается',
        'done': 'выполнен',
        'failed': 'ошибка обработки',
    }
    label = status_labels.get(status, status)

    notif = Notification.objects.create(
        user_id=user_id,
        notification_type=Notification.TYPE_ORDER,
        title=f'Заказ #{order_id} — {label}',
        message=f'Статус вашего заказа #{order_id} изменён на «{label}».',
        link=f'/orders/{order_id}/',
    )
    invalidate_unread(user_id)

    _push_notification_ws(user_id, {
        'id': notif.id,
        'notification_type': notif.notification_type,
        'title': notif.title,
        'link': notif.link,
        'created_at': notif.created_at.strftime('%d.%m %H:%M'),
    })

    logger.info(f"[NOTIF] Order status → user {user_id}: order #{order_id} → {status}")


@shared_task
def notify_chat_message(recipient_id, room_id, sender_name, text_preview):
    """
    Уведомление о новом сообщении в чате.
    RabbitMQ → Celery → PostgreSQL + Redis + WebSocket.
    """
    from .models import Notification

    notif = Notification.objects.create(
        user_id=recipient_id,
        notification_type=Notification.TYPE_CHAT,
        title=f'Сообщение от {sender_name}',
        message=text_preview[:100],
        link=f'/chat/{room_id}/',
    )
    invalidate_unread(recipient_id)

    _push_notification_ws(recipient_id, {
        'id': notif.id,
        'notification_type': notif.notification_type,
        'title': notif.title,
        'link': notif.link,
        'created_at': notif.created_at.strftime('%d.%m %H:%M'),
    })

    logger.info(f"[NOTIF] Chat message → user {recipient_id}: room #{room_id}")


@shared_task
def notify_new_chat_for_moderators(room_id, username):
    """
    Уведомить всех модераторов/админов о новом чате.
    RabbitMQ → Celery → PostgreSQL + Redis + WebSocket.
    """
    from django.contrib.auth.models import User
    from users.models import UserProfile
    from .models import Notification

    staff_users = User.objects.filter(
        profile__role__in=[UserProfile.ROLE_MODERATOR, UserProfile.ROLE_ADMIN],
    ).values_list('id', flat=True)

    for uid in staff_users:
        notif = Notification.objects.create(
            user_id=uid,
            notification_type=Notification.TYPE_CHAT,
            title=f'Новый чат от {username}',
            message=f'Пользователь {username} начал чат поддержки.',
            link=f'/chat/{room_id}/',
        )
        invalidate_unread(uid)
        _push_notification_ws(uid, {
            'id': notif.id,
            'notification_type': notif.notification_type,
            'title': notif.title,
            'link': notif.link,
            'created_at': notif.created_at.strftime('%d.%m %H:%M'),
        })

    logger.info(f"[NOTIF] New chat #{room_id} → {len(staff_users)} staff users")


@shared_task
def notify_user(order_id):
    """Обратная совместимость: вызывается из finish_order."""
    from orders.models import Order
    order = Order.objects.get(id=order_id)
    notify_order_status.delay(order.user_id, order.id, order.status)
