from django.contrib import admin
from .models import Notification, WebPushSubscription, WebPushMessage


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'read', 'created_at']
    list_filter = ['notification_type', 'read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username', 'recipient__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('recipient', 'title', 'message', 'notification_type')
        }),
        ('Статус', {
            'fields': ('read', 'created_at')
        }),
        ('Дополнительно', {
            'fields': ('related_object_id', 'related_object_type', 'action_url'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'device_name', 'endpoint']
    readonly_fields = ['created_at', 'endpoint', 'p256dh_key', 'auth_key', 'user_agent']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'device_name', 'is_active')
        }),
        ('Подписка', {
            'fields': ('endpoint', 'p256dh_key', 'auth_key'),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['deactivate_subscriptions', 'activate_subscriptions']
    
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Деактивировано {updated} подписок.'
        )
    deactivate_subscriptions.short_description = "Деактивировать выбранные подписки"
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Активировано {updated} подписок.'
        )
    activate_subscriptions.short_description = "Активировать выбранные подписки"


@admin.register(WebPushMessage)
class WebPushMessageAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'title', 'success', 'sent_at']
    list_filter = ['success', 'sent_at']
    search_fields = ['title', 'body', 'subscription__user__username']
    readonly_fields = ['sent_at', 'subscription', 'notification', 'title', 'body',
                       'success', 'error_message']
    ordering = ['-sent_at']
    
    fieldsets = (
        (None, {
            'fields': ('subscription', 'notification', 'title', 'body')
        }),
        ('Результат', {
            'fields': ('success', 'error_message', 'sent_at')
        }),
    )
    
    def has_add_permission(self, request):
        # Запрещаем создание вручную
        return False
    
    def has_change_permission(self, request, obj=None):
        # Запрещаем редактирование
        return False
