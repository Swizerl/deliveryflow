from django.contrib import admin

from .models import ChatRoom, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('sender', 'text', 'is_read', 'created_at')


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'moderator', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'text_short', 'is_read', 'created_at')
    list_filter = ('is_read', 'room')

    def text_short(self, obj):
        return obj.text[:80]
    text_short.short_description = 'Текст'
