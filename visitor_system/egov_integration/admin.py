# egov_integration/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
import json
from .models import DocumentVerification, EgovAPILog, EgovSettings


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'document_type', 'status', 'guest_link', 
        'requested_by', 'created_at', 'verified_at'
    ]
    list_filter = ['status', 'document_type', 'created_at']
    search_fields = ['guest__full_name', 'requested_by__username']
    readonly_fields = [
        'id', 'created_at', 'verified_at', 'egov_response_formatted',
        'verified_data_formatted'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'guest', 'document_type', 'status')
        }),
        ('Проверка', {
            'fields': ('requested_by', 'created_at', 'verified_at', 'retry_count')
        }),
        ('Результаты', {
            'fields': ('verified_data_formatted', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Технические данные', {
            'fields': ('egov_response_formatted',),
            'classes': ('collapse',)
        }),
    )
    
    def guest_link(self, obj):
        if obj.guest:
            url = reverse('admin:visitors_guest_change', args=[obj.guest.pk])
            return format_html('<a href="{}">{}</a>', url, obj.guest.full_name)
        return '-'
    guest_link.short_description = 'Гость'
    
    def egov_response_formatted(self, obj):
        if obj.egov_response:
            formatted = json.dumps(obj.egov_response, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    egov_response_formatted.short_description = 'Ответ egov.kz'
    
    def verified_data_formatted(self, obj):
        if obj.verified_data:
            formatted = json.dumps(obj.verified_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    verified_data_formatted.short_description = 'Проверенные данные'


@admin.register(EgovAPILog)
class EgovAPILogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'method', 'endpoint_short', 'response_status', 
        'response_time_ms', 'user', 'success_indicator'
    ]
    list_filter = ['method', 'response_status', 'created_at']
    search_fields = ['endpoint', 'user__username']
    readonly_fields = [
        'id', 'created_at', 'request_data_formatted', 
        'response_data_formatted', 'response_time_ms'
    ]
    
    fieldsets = (
        ('Запрос', {
            'fields': ('method', 'endpoint', 'created_at', 'user', 'ip_address')
        }),
        ('Ответ', {
            'fields': ('response_status', 'response_time_ms', 'verification')
        }),
        ('Данные запроса', {
            'fields': ('request_data_formatted',),
            'classes': ('collapse',)
        }),
        ('Данные ответа', {
            'fields': ('response_data_formatted',),
            'classes': ('collapse',)
        }),
    )
    
    def endpoint_short(self, obj):
        if len(obj.endpoint) > 50:
            return obj.endpoint[:47] + '...'
        return obj.endpoint
    endpoint_short.short_description = 'Endpoint'
    
    def success_indicator(self, obj):
        if obj.is_success():
            return format_html(
                '<span style="color: green;">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗</span>'
            )
    success_indicator.short_description = 'Успех'
    
    def request_data_formatted(self, obj):
        if obj.request_data:
            formatted = json.dumps(obj.request_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    request_data_formatted.short_description = 'Данные запроса'
    
    def response_data_formatted(self, obj):
        if obj.response_data:
            formatted = json.dumps(obj.response_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted)
        return '-'
    response_data_formatted.short_description = 'Данные ответа'


@admin.register(EgovSettings)
class EgovSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_encrypted', 'updated_at', 'updated_by']
    list_filter = ['is_encrypted', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Настройка', {
            'fields': ('name', 'description', 'is_encrypted')
        }),
        ('Значение', {
            'fields': ('value',)
        }),
        ('Метаданные', {
            'fields': ('updated_at', 'updated_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)