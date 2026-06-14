def menu_changed_event(action, product_id, user_id=None):
    from .tasks import process_menu_change

    process_menu_change.delay(action, product_id, user_id)
