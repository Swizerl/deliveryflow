from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_menu_update(action, product_id):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        'menu_updates',
        {
            'type': 'menu.update',
            'action': action,
            'product_id': product_id,
        },
    )
