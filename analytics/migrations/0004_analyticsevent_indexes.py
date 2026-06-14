from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_alter_analyticsevent_event_type'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['-created_at'], name='analytics_created_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['event_type'], name='analytics_event_type_idx'),
        ),
    ]
