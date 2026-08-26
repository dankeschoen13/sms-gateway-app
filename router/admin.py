from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_number', 'department', 'is_blocked', 'timestamp')
    list_filter = ('department', 'is_blocked', 'timestamp')
    search_fields = ('sender_number', 'message_body')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)