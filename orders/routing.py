from django.urls import re_path

from .consumers import OrderStatusConsumer, UserOrdersConsumer

websocket_urlpatterns = [
    re_path(r'^(?P<order_id>\d+)/$', OrderStatusConsumer.as_asgi()),
    re_path(r'^$', UserOrdersConsumer.as_asgi()),
]
