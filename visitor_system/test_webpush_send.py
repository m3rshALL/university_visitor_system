#!/usr/bin/env python
"""Тестовая отправка WebPush уведомления"""
import os
import sys
import django
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.insert(0, str(Path(__file__).parent))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from django.contrib.auth.models import User
from notifications.utils import send_webpush_notification

print("=== ТЕСТ WEBPUSH УВЕДОМЛЕНИЯ ===")

# Находим пользователя admin
try:
    admin_user = User.objects.get(username='admin')
    print(f"✓ Пользователь admin найден")
except User.DoesNotExist:
    print("✗ Пользователь admin не найден!")
    sys.exit(1)

# Проверяем подписки
from notifications.models import WebPushSubscription
subscriptions = WebPushSubscription.objects.filter(user=admin_user, is_active=True)
print(f"✓ Активных подписок у admin: {subscriptions.count()}")

if not subscriptions.exists():
    print("✗ У пользователя admin нет активных WebPush подписок!")
    print("Зайдите на сайт и включите уведомления")
    sys.exit(1)

# Отправляем тестовое уведомление
print("\n📤 Отправляю тестовое WebPush уведомление...")

result = send_webpush_notification(
    user=admin_user,
    title="🧪 Тестовое уведомление",
    body="Если вы видите это уведомление, WebPush работает корректно!",
    data={
        'test': True,
        'type': 'test_notification'
    }
)

print(f"📊 Результат отправки:")
print(f"  - Успешно: {result['success']}")
print(f"  - Отправлено: {result['sent_count']}")
print(f"  - Ошибки: {len(result['errors'])}")

if result['errors']:
    print("❌ Ошибки:")
    for error in result['errors']:
        print(f"  - {error}")

if result['success']:
    print("\n✅ УСПЕХ! WebPush уведомление отправлено!")
    print("Проверьте браузер - должно появиться уведомление")
else:
    print("\n❌ ОШИБКА! WebPush уведомление не отправлено")
    print("Проверьте логи сервера и настройки браузера")
