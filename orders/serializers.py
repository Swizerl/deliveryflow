from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from orders.realtime import invalidate_products_cache
from products.models import Product
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_price',
            'quantity',
            'line_total',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['line_total'] = str(instance.line_total)
        return data


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'created_at', 'items', 'total_price']
        read_only_fields = ['user', 'status', 'created_at', 'items', 'total_price']

    def get_total_price(self, obj):
        # Считаем по уже подгруженным items (prefetch_related) — без лишних SQL-запросов.
        return sum(item.quantity * item.product.price for item in obj.items.all())


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)


class CreateOrderSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один товар.')
        return value

    def validate(self, attrs):
        # Быстрая предварительная проверка остатков (без блокировки).
        # Финальная гарантия — атомарный update в create().
        items = attrs['items']
        for entry in items:
            product = entry['product']
            qty = entry['quantity']
            if product.stock < qty:
                raise serializers.ValidationError(
                    f'Недостаточно «{product.name}» на складе (осталось {product.stock}).'
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        order = Order.objects.create(user=user)
        for entry in validated_data['items']:
            product = entry['product']
            qty = entry['quantity']
            OrderItem.objects.create(order=order, product=product, quantity=qty)
            # Атомарное списание остатка — защита от гонки при параллельных заказах.
            updated = Product.objects.filter(
                id=product.id, stock__gte=qty
            ).update(stock=F('stock') - qty)
            if not updated:
                raise serializers.ValidationError(
                    f'Недостаточно «{product.name}» на складе.'
                )
        invalidate_products_cache()
        return order
