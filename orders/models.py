from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F, DecimalField
from products.models import Product


class Order(models.Model):

    STATUS_CREATED = 'created'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Created'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='order_created_idx'),
            models.Index(fields=['status'], name='order_status_idx'),
            models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
        ]

    def __str__(self):
        return f"Order {self.id} - {self.status}"

    @property
    def total_price(self):
        total = self.items.aggregate(
            sum=Sum(F('quantity') * F('product__price'), output_field=DecimalField())
        )['sum']
        return total or 0


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_order_product',
            ),
        ]

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def line_total(self):
        return self.product.price * self.quantity
