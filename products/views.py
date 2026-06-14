from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.permissions import IsAdminRole
from orders.realtime import PRODUCTS_LIST_CACHE_KEY
from .events import menu_changed_event
from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdminRole()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        cached = cache.get(PRODUCTS_LIST_CACHE_KEY)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(PRODUCTS_LIST_CACHE_KEY, response.data, timeout=60)
        return response

    def perform_create(self, serializer):
        product = serializer.save()
        menu_changed_event('created', product.id, self.request.user.id)

    def perform_update(self, serializer):
        product = serializer.save()
        menu_changed_event('updated', product.id, self.request.user.id)

    def perform_destroy(self, instance):
        product_id = instance.id
        user_id = self.request.user.id
        instance.delete()
        menu_changed_event('deleted', product_id, user_id)
