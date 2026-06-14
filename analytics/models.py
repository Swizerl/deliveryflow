from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    EVENT_ORDER = 'order_completed'
    EVENT_MENU = 'menu_changed'
    EVENT_ROLE = 'role_changed'
    EVENT_CHAT = 'chat_message'

    EVENT_CHOICES = [
        (EVENT_ORDER, 'Заказ'),
        (EVENT_MENU, 'Меню'),
        (EVENT_ROLE, 'Смена роли'),
        (EVENT_CHAT, 'Сообщение в чате'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='analytics_created_idx'),
            models.Index(fields=['event_type'], name='analytics_event_type_idx'),
        ]

    def __str__(self):
        return f'{self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}'
