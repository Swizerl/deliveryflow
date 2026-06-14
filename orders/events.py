def order_created_event(order_id):
    from .tasks import process_order

    process_order.delay(order_id)
