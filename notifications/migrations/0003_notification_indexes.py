from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_alter_notification_options_remove_notification_order_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at'], name='notif_user_created_idx'),
        ),
    ]
