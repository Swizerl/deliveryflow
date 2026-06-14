import logging

from celery import shared_task
from django.conf import settings

from analytics.tasks import log_event
from notifications.tasks import notify_user, notify_order_status
from .models import Order
from .realtime import broadcast_order_status, invalidate_order_stats_cache

logger = logging.getLogger(__name__)

# Задержка между статусами "processing" и "done".
# Это НЕ занятость воркера, а отложенный запуск следующего шага (latency),
# поэтому пропускная способность системы от этого значения не зависит.
# 3 сек — для демонстрации; для "реалистичных" 50 минут поставьте 3000.
PROCESSING_DELAY = getattr(settings, 'ORDER_PROCESSING_DELAY_SECONDS', 3)


def _update_order_status(order, status):
    order.status = status
    order.save(update_fields=['status'])
    invalidate_order_stats_cache()
    broadcast_order_status(order)
    # Асинхронное уведомление пользователю через RabbitMQ → Celery → Redis → WebSocket.
    notify_order_status.delay(order.user_id, order.id, status)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    acks_late=True,
)
def process_order(self, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"[ORDER SERVICE] Order {order_id} not found, skipping.")
        return

    # Заказ уже доведён до конца — повторная доставка сообщения из RabbitMQ.
    if order.status in (Order.STATUS_DONE, Order.STATUS_FAILED):
        logger.info(f"[ORDER SERVICE] Order {order_id} already '{order.status}', skipping.")
        return

    try:
        # В processing переводим только из created (идемпотентность).
        # Если заказ уже в processing (ретрай после сбоя на этапе постановки
        # задачи) — просто перепланируем завершение, не теряя заказ.
        if order.status == Order.STATUS_CREATED:
            logger.info(f"[ORDER SERVICE] Processing order {order_id}")
            _update_order_status(order, Order.STATUS_PROCESSING)

        # Воркер НЕ блокируется на время "обработки/доставки".
        # Завершение запланировано с задержкой через брокер: процесс-воркер
        # сразу свободен и может взять следующий заказ. "Время доставки" — это
        # latency, а не занятость воркера, поэтому throughput не упирается
        # в число воркеров (в отличие от блокирующего time.sleep).
        finish_order.apply_async((order_id,), countdown=PROCESSING_DELAY)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"[ORDER SERVICE] Order {order_id} failed: {exc}")
            _update_order_status(order, Order.STATUS_FAILED)
            return
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    acks_late=True,
)
def finish_order(self, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"[ORDER SERVICE] Order {order_id} not found, skipping.")
        return

    if order.status in (Order.STATUS_DONE, Order.STATUS_FAILED):
        logger.info(f"[ORDER SERVICE] Order {order_id} already '{order.status}', skipping.")
        return

    try:
        _update_order_status(order, Order.STATUS_DONE)
        logger.info(f"[ORDER SERVICE] Order {order_id} completed")
        log_event.delay(order_id)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"[ORDER SERVICE] Order {order_id} finish failed: {exc}")
            _update_order_status(order, Order.STATUS_FAILED)
            return
        raise
