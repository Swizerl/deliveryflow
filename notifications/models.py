from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_ORDER = 'order_status'
    TYPE_CHAT = 'chat_message'
    TYPE_SYSTEM = 'system'

    TYPE_CHOICES = [
        (TYPE_ORDER, 'Статус заказа'),
        (TYPE_CHAT, 'Сообщение в чате'),
        (TYPE_SYSTEM, 'Системное'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_ORDER,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default='')
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
            models.Index(fields=['user', '-created_at'], name='notif_user_created_idx'),
        ]

    def __str__(self):
        return f'[{self.notification_type}] {self.title}'
