from django.core.cache import cache
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import user_is_admin
from .events import order_created_event
from .models import Order
from .realtime import (
    ORDER_STATS_CACHE_KEY,
    broadcast_order_status,
    invalidate_order_stats_cache,
)
from .serializers import CreateOrderSerializer, OrderSerializer


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        order = serializer.save()

        invalidate_order_stats_cache()
        broadcast_order_status(order)
        order_created_event(order.id)

        return Response(
            OrderSerializer(order).data,
            status=201,
        )


class OrderListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = OrderListPagination

    def get_queryset(self):
        qs = Order.objects.select_related('user').prefetch_related('items__product')
        if user_is_admin(self.request.user):
            return qs
        return qs.filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.prefetch_related('items__product')
        if user_is_admin(self.request.user):
            return qs
        return qs.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_stats(request):
    stats = cache.get(ORDER_STATS_CACHE_KEY)

    if stats is None:
        stats = {"total_orders": Order.objects.count()}
        cache.set(ORDER_STATS_CACHE_KEY, stats, timeout=30)
        source = "database"
    else:
        source = "redis cache"

    return Response({"data": stats, "source": source})
