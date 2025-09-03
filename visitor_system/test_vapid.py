#!/usr/bin/env python
"""
Тестовый скрипт для проверки загрузки VAPID ключей
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append('/d/university_visitor_system/visitor_system')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from django.conf import settings

print("=== Проверка VAPID настроек ===")
print(f"WEBPUSH_SETTINGS: {getattr(settings, 'WEBPUSH_SETTINGS', 'НЕ НАЙДЕНО')}")

if hasattr(settings, 'WEBPUSH_SETTINGS'):
    webpush_settings = settings.WEBPUSH_SETTINGS
    print(f"VAPID_PUBLIC_KEY: {webpush_settings.get('VAPID_PUBLIC_KEY', 'НЕ НАЙДЕНО')[:50]}...")
    print(f"VAPID_PRIVATE_KEY: {webpush_settings.get('VAPID_PRIVATE_KEY', 'НЕ НАЙДЕНО')[:50]}...")
    print(f"VAPID_ADMIN_EMAIL: {webpush_settings.get('VAPID_ADMIN_EMAIL', 'НЕ НАЙДЕНО')}")

print("\n=== Проверка переменных окружения ===")
print(f"VAPID_PUBLIC_KEY env: {os.getenv('VAPID_PUBLIC_KEY', 'НЕ НАЙДЕНО')[:50]}...")
print(f"VAPID_PRIVATE_KEY env: {os.getenv('VAPID_PRIVATE_KEY', 'НЕ НАЙДЕНО')[:50]}...")
print(f"VAPID_ADMIN_EMAIL env: {os.getenv('VAPID_ADMIN_EMAIL', 'НЕ НАЙДЕНО')}")
