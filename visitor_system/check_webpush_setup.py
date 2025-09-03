#!/usr/bin/env python
"""Проверка настроек WebPush уведомлений"""
import os
import sys
import django
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.insert(0, str(Path(__file__).parent))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from django.contrib.auth.models import User, Group
from notifications.models import WebPushSubscription

print("=== ПРОВЕРКА WEBPUSH УВЕДОМЛЕНИЙ ===")

# 1. Проверяем группу Reception
print("\n1. ГРУППА RECEPTION:")
try:
    reception_group = Group.objects.get(name="Reception")
    reception_users = reception_group.user_set.filter(is_active=True)
    print(f"✓ Группа Reception найдена")
    print(f"✓ Активных пользователей в группе: {reception_users.count()}")
    
    for user in reception_users:
        print(f"  - {user.username} ({user.get_full_name() or 'Без имени'}) - {user.email or 'Без email'}")
        
except Group.DoesNotExist:
    print("✗ ОШИБКА: Группа Reception не найдена!")
    print("  Создайте группу Reception в админке Django")

# 2. Проверяем WebPush подписки
print("\n2. WEBPUSH ПОДПИСКИ:")
subscriptions = WebPushSubscription.objects.filter(is_active=True)
print(f"✓ Активных подписок: {subscriptions.count()}")

if subscriptions.exists():
    for sub in subscriptions:
        print(f"  - {sub.user.username} ({sub.device_name}) - создана {sub.created_at.strftime('%Y-%m-%d %H:%M')}")
else:
    print("✗ НЕТ АКТИВНЫХ ПОДПИСОК!")
    print("  Пользователи должны включить уведомления в браузере")

# 3. Проверяем всех пользователей с подписками
print("\n3. ПОЛЬЗОВАТЕЛИ С WEBPUSH ПОДПИСКАМИ:")
users_with_subscriptions = User.objects.filter(
    webpush_subscriptions__is_active=True
).distinct()

for user in users_with_subscriptions:
    user_subs = user.webpush_subscriptions.filter(is_active=True)
    print(f"  - {user.username}: {user_subs.count()} подписок")
    
    # Проверяем, в каких группах состоит пользователь
    groups = user.groups.all()
    if groups.exists():
        group_names = [g.name for g in groups]
        print(f"    Группы: {', '.join(group_names)}")
    else:
        print("    Группы: нет")

# 4. Проверяем настройки WEBPUSH
print("\n4. НАСТРОЙКИ WEBPUSH:")
from django.conf import settings
webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
print(f"✓ VAPID_PUBLIC_KEY: {'ЕСТЬ' if webpush_settings.get('VAPID_PUBLIC_KEY') else 'НЕТ'}")
print(f"✓ VAPID_PRIVATE_KEY: {'ЕСТЬ' if webpush_settings.get('VAPID_PRIVATE_KEY') else 'НЕТ'}")
print(f"✓ VAPID_ADMIN_EMAIL: {webpush_settings.get('VAPID_ADMIN_EMAIL', 'НЕТ')}")

print("\n=== РЕКОМЕНДАЦИИ ===")
if not Group.objects.filter(name="Reception").exists():
    print("1. Создайте группу Reception в админке Django")
    
if not subscriptions.exists():
    print("2. Пользователи должны зайти на сайт и включить уведомления")
    
if not users_with_subscriptions.exists():
    print("3. Проверьте, что пользователи дали разрешение на уведомления в браузере")

print("\n4. Для тестирования:")
print("   - Зайдите на http://127.0.0.1:8000/visitors/dashboard/")
print("   - Включите уведомления (разрешите в браузере)")
print("   - Зарегистрируйте тестового гостя")
print("   - Уведомление должно прийти!")
