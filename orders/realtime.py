from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

ORDER_STATS_CACHE_KEY = "order_stats"
PRODUCTS_LIST_CACHE_KEY = "products:list"
MENU_PAGE_CACHE_KEY = "menu:categories"


def invalidate_order_stats_cache():
    cache.delete(ORDER_STATS_CACHE_KEY)


def invalidate_products_cache():
    # Чистим и API-кэш каталога, и кэш HTML-страницы меню одним вызовом,
    # чтобы изменения товаров/остатков не оставались устаревшими ни там, ни там.
    cache.delete_many([PRODUCTS_LIST_CACHE_KEY, MENU_PAGE_CACHE_KEY])


def broadcast_order_status(order):
    """Отправка обновления статуса заказа в WebSocket-группу через Redis."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = {
        "type": "order.status",
        "order_id": order.id,
        "status": order.status,
        "user_id": order.user_id,
    }
    async_to_sync(channel_layer.group_send)(f"order_{order.id}", payload)

    user_payload = {
        "type": "order.status",
        "order_id": order.id,
        "status": order.status,
    }
    async_to_sync(channel_layer.group_send)(
        f"user_orders_{order.user_id}",
        user_payload,
    )
