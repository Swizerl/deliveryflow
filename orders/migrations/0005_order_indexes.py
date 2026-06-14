from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_alter_order_options_alter_order_user'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['-created_at'], name='order_created_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='order_status_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
        ),
    ]
