from django.contrib import admin
from django.utils.html import format_html
import json
from .models import DashboardMetric, RealtimeEvent, DashboardWidget


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = [
        'metric_type', 'timestamp', 'is_active', 'value_preview'
    ]
    list_filter = ['metric_type', 'is_active', 'timestamp']
    search_fields = ['metric_type']
    readonly_fields = ['timestamp', 'value_formatted']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('metric_type', 'is_active', 'timestamp')
        }),
        ('Данные', {
            'fields': ('value', 'value_formatted',),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        if isinstance(obj.value, dict):
            # Показываем краткую информацию
            preview = {}
            for key, value in list(obj.value.items())[:3]:
                if isinstance(value, (int, float, str)):
                    preview[key] = value
            return json.dumps(preview, ensure_ascii=False)[:50] + '...'
        return str(obj.value)[:50] + '...'
    value_preview.short_description = 'Предварительный просмотр'
    
    def value_formatted(self, obj):
        if obj.value:
            formatted = json.dumps(obj.value, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    value_formatted.short_description = 'Значение (форматированное)'


@admin.register(RealtimeEvent)
class RealtimeEventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'event_type', 'priority', 'user', 'is_read', 'created_at'
    ]
    list_filter = ['event_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'data_formatted']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('event_type', 'priority', 'title', 'message')
        }),
        ('Связи', {
            'fields': ('user', 'visit')
        }),
        ('Статус', {
            'fields': ('is_read', 'created_at')
        }),
        ('Дополнительные данные', {
            'fields': ('data_formatted',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Отмечено как прочитанное: {updated} событий')
    mark_as_read.short_description = 'Отметить как прочитанное'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Отмечено как непрочитанное: {updated} событий')
    mark_as_unread.short_description = 'Отметить как непрочитанное'
    
    def data_formatted(self, obj):
        if obj.data:
            formatted = json.dumps(obj.data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    data_formatted.short_description = 'Дополнительные данные'


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'widget_type', 'position_info', 'size_info', 
        'is_active', 'refresh_interval', 'created_by'
    ]
    list_filter = ['widget_type', 'is_active', 'created_at']
    search_fields = ['name', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'config_formatted']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'widget_type', 'title', 'description', 'is_active')
        }),
        ('Позиционирование', {
            'fields': ('position_x', 'position_y', 'width', 'height')
        }),
        ('Настройки', {
            'fields': ('refresh_interval', 'config_formatted')
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def position_info(self, obj):
        return f"({obj.position_x}, {obj.position_y})"
    position_info.short_description = 'Позиция (X, Y)'
    
    def size_info(self, obj):
        return f"{obj.width}×{obj.height}"
    size_info.short_description = 'Размер'
    
    def config_formatted(self, obj):
        if obj.config:
            formatted = json.dumps(obj.config, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    config_formatted.short_description = 'Конфигурация'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
