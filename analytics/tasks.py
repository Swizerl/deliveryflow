import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.cache import cache

from .dashboard import ANALYTICS_DASHBOARD_KEY, build_dashboard_stats
from .models import AnalyticsEvent

logger = logging.getLogger(__name__)

# Троттлинг пересчёта дашборда: при потоке заказов не пересчитываем статистику
# на каждое событие, а не чаще одного раза в этот интервал (секунды).
ANALYTICS_REFRESH_LOCK = 'analytics:refresh:lock'
ANALYTICS_REFRESH_THROTTLE = 10


@shared_task
def refresh_analytics_dashboard():
    data = build_dashboard_stats()
    cache.set(ANALYTICS_DASHBOARD_KEY, data, timeout=300)
    return data


def schedule_analytics_refresh():
    # cache.add атомарен (Redis SET NX): если ключ уже стоит — значит пересчёт
    # недавно запланирован, выходим. Так поток заказов даёт максимум один
    # пересчёт в ANALYTICS_REFRESH_THROTTLE секунд вместо одного на каждый заказ.
    try:
        if not cache.add(ANALYTICS_REFRESH_LOCK, '1', ANALYTICS_REFRESH_THROTTLE):
            return
    except Exception:
        pass
    try:
        refresh_analytics_dashboard.delay()
    except Exception:
        try:
            data = build_dashboard_stats()
            cache.set(ANALYTICS_DASHBOARD_KEY, data, timeout=300)
        except Exception:
            pass


@shared_task
def log_event(order_id):
    from orders.models import Order

    order = Order.objects.get(id=order_id)
    AnalyticsEvent.objects.create(
        event_type=AnalyticsEvent.EVENT_ORDER,
        payload={
            'order_id': order.id,
            'status': order.status,
            'user_id': order.user_id,
        },
        user_id=order.user_id,
    )
    schedule_analytics_refresh()


@shared_task
def log_menu_change(action, product_id, user_id=None):
    AnalyticsEvent.objects.create(
        event_type=AnalyticsEvent.EVENT_MENU,
        payload={
            'action': action,
            'product_id': product_id,
        },
        user_id=user_id,
    )
    schedule_analytics_refresh()


@shared_task
def log_role_change(user_id, old_role, new_role):
    """
    Асинхронное логирование смены роли.
    RabbitMQ (брокер) → Celery (воркер) → PostgreSQL (лог) + Redis (инвалидация кэша)
    + WebSocket (уведомление пользователю).
    """
    from users.permissions import invalidate_role_cache

    # 1. Записываем событие в БД.
    AnalyticsEvent.objects.create(
        event_type=AnalyticsEvent.EVENT_ROLE,
        payload={
            'user_id': user_id,
            'old_role': old_role,
            'new_role': new_role,
        },
        user_id=user_id,
    )
    logger.info(f"[ANALYTICS] Role changed: user {user_id}: {old_role} → {new_role}")

    # 2. Инвалидируем Redis-кэш роли пользователя.
    invalidate_role_cache(user_id)

    # 3. Отправляем WebSocket-уведомление пользователю через Redis Channel Layer.
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_notifications_{user_id}',
            {
                'type': 'role.changed',
                'old_role': old_role,
                'new_role': new_role,
            },
        )
    except Exception as exc:
        logger.warning(f"[ANALYTICS] WS notification failed for user {user_id}: {exc}")

    # 4. Обновляем кэш аналитики.
    schedule_analytics_refresh()
