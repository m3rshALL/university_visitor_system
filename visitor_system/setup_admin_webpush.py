#!/usr/bin/env python
"""Добавление пользователя в группу Reception для получения WebPush уведомлений"""
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

print("=== НАСТРОЙКА WEBPUSH УВЕДОМЛЕНИЙ ===")

# Получаем пользователя admin
try:
    admin_user = User.objects.get(username='admin')
    print(f"✓ Пользователь admin найден: {admin_user.get_full_name() or admin_user.username}")
except User.DoesNotExist:
    print("✗ Пользователь admin не найден!")
    print("Создайте суперпользователя: python manage.py createsuperuser")
    sys.exit(1)

# Получаем группу Reception
try:
    reception_group = Group.objects.get(name='Reception')
    print(f"✓ Группа Reception найдена")
except Group.DoesNotExist:
    print("✗ Группа Reception не найдена, создаю...")
    reception_group = Group.objects.create(name='Reception')
    print("✓ Группа Reception создана")

# Добавляем пользователя в группу
if admin_user.groups.filter(name='Reception').exists():
    print("✓ Пользователь admin уже в группе Reception")
else:
    admin_user.groups.add(reception_group)
    print("✓ Пользователь admin добавлен в группу Reception")

# Проверяем результат
reception_users = reception_group.user_set.all()
print(f"\n📋 Пользователи в группе Reception ({reception_users.count()}):")
for user in reception_users:
    has_subscription = hasattr(user, 'webpush_subscriptions') and user.webpush_subscriptions.filter(is_active=True).exists()
    sub_status = "✓ Подписан на WebPush" if has_subscription else "❌ Не подписан на WebPush"
    print(f"  - {user.username} ({user.get_full_name() or 'Без имени'}) - {sub_status}")

print(f"\n🎯 ГОТОВО! Теперь пользователь admin будет получать WebPush уведомления о:")
print("  - Регистрации новых гостей")
print("  - Регистрации студентов/абитуриентов")
print("  - Выходе гостей и студентов")

print(f"\n📱 Для тестирования:")
print("1. Зайдите как admin на http://127.0.0.1:8000/visitors/dashboard/")
print("2. Убедитесь, что уведомления включены")
print("3. Зарегистрируйте тестового гостя")
print("4. WebPush уведомление должно прийти!")
