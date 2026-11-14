from django.contrib import admin

from .models import SMSMessage


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'short_body', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('recipient', 'body', 'provider_message_id')
    readonly_fields = ('provider_message_id', 'created_at', 'updated_at')

    @admin.display(description='Message')
    def short_body(self, obj):
        return obj.body if len(obj.body) <= 50 else obj.body[:47] + '...'
