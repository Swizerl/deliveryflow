from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    """Комната чата: один пользователь ↔ один модератор."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_user',
        verbose_name='Пользователь',
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms_as_moderator',
        verbose_name='Модератор',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        mod = self.moderator.username if self.moderator else '—'
        return f'Чат #{self.id}: {self.user.username} ↔ {mod}'


class ChatMessage(models.Model):
    """Одно сообщение в чате."""

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    text = models.TextField(verbose_name='Текст')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return f'[{self.sender.username}] {self.text[:50]}'
