from celery import shared_task

from analytics.tasks import log_menu_change
from orders.realtime import invalidate_products_cache
from .realtime import broadcast_menu_update


@shared_task
def process_menu_change(action, product_id, user_id=None):
    """
    Асинхронная обработка изменения меню (RabbitMQ → Celery):
    - инвалидация Redis-кэша каталога;
    - WebSocket-уведомление клиентам;
    - запись события в аналитику.
    """
    invalidate_products_cache()
    broadcast_menu_update(action, product_id)
    log_menu_change.delay(action, product_id, user_id)
