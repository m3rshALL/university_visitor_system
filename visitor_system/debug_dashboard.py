#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

print("=== ОТЛАДКА ДЛЯ ПАНЕЛИ СОТРУДНИКА ===")

# Импортируем модели
from django.contrib.auth.models import User
from visitors.models import GuestInvitation

# Получаем пользователя sagat.akimbay
try:
    user_sagat = User.objects.get(username='sagat.akimbay')
    print(f"Пользователь найден: {user_sagat.username} (ID: {user_sagat.id})")
except User.DoesNotExist:
    print("Пользователь sagat.akimbay не найден!")
    exit(1)

# Проверяем приглашения для этого пользователя
invitations = GuestInvitation.objects.filter(employee=user_sagat)
print(f"Всего приглашений для {user_sagat.username}: {invitations.count()}")

# Проверяем заполненные приглашения, ожидающие финализации
pending_invitations = GuestInvitation.objects.filter(
    employee=user_sagat,
    is_filled=True,
    is_registered=False
)
print(f"Заполненных и ожидающих регистрации: {pending_invitations.count()}")

# Вывод деталей приглашений
print("\nДетали приглашений:")
for inv in pending_invitations:
    print(f"ID: {inv.id}")
    print(f"Гость: {inv.guest_full_name}")
    print(f"Заполнено: {inv.is_filled}")
    print(f"Зарегистрировано: {inv.is_registered}")
    print(f"Создано: {inv.created_at}")
    print("-" * 40)

# Проверяем все поля модели GuestInvitation
print("\nСтруктура модели GuestInvitation:")
fields = GuestInvitation._meta.get_fields()
print(f"Всего полей: {len(fields)}")
for field in fields:
    print(f"- {field.name}")

# Проверим содержимое шаблона
print("\nОтладка сеанса:")
from django.contrib.sessions.models import Session
sessions = Session.objects.all()
print(f"Активных сессий: {sessions.count()}")
for s in sessions:
    print(f"ID сессии: {s.session_key}")
    print(f"Истекает: {s.expire_date}")
