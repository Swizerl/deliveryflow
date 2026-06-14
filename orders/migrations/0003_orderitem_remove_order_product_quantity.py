import django.db.models.deletion
from django.db import migrations, models


def copy_legacy_items(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    OrderItem = apps.get_model('orders', 'OrderItem')
    for order in Order.objects.all():
        if getattr(order, 'product_id', None):
            OrderItem.objects.get_or_create(
                order_id=order.id,
                product_id=order.product_id,
                defaults={'quantity': order.quantity or 1},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_alter_product_name'),
        ('orders', '0002_alter_order_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.product')),
            ],
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.UniqueConstraint(fields=('order', 'product'), name='unique_order_product'),
        ),
        migrations.RunPython(copy_legacy_items, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='order',
            name='product',
        ),
        migrations.RemoveField(
            model_name='order',
            name='quantity',
        ),
    ]
