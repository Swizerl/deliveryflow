import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delivery.settings')

django_asgi_app = get_asgi_application()

from chat.routing import websocket_urlpatterns as chat_ws  # noqa: E402
from notifications.routing import websocket_urlpatterns as notif_ws  # noqa: E402
from orders.routing import websocket_urlpatterns as order_ws  # noqa: E402
from products.consumers import MenuUpdatesConsumer  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                path('ws/menu/', MenuUpdatesConsumer.as_asgi()),
                path('ws/orders/', URLRouter(order_ws)),
                path('ws/chat/', URLRouter(chat_ws)),
                path('ws/notifications/', URLRouter(notif_ws)),
            ])
        )
    ),
})
