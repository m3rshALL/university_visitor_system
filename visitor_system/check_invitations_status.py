#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from visitors.models import GuestInvitation
from django.contrib.auth.models import User

print("=== Проверка состояния приглашений гостей ===")

# Получить всех пользователей
users = User.objects.all()
print(f"\nВсего пользователей: {users.count()}")
for user in users:
    print(f"- {user.username} (email: {user.email})")

# Получить все приглашения
invitations = GuestInvitation.objects.all()
print(f"\nВсего приглашений: {invitations.count()}")

filled_invitations = invitations.filter(is_filled=True)
print(f"Заполненных приглашений: {filled_invitations.count()}")

pending_invitations = invitations.filter(is_filled=True, is_registered=False)
print(f"Ожидающих приглашений (filled=True, registered=False): {pending_invitations.count()}")

print("\n=== Детали ожидающих приглашений ===")
for inv in pending_invitations:
    print(f"ID: {inv.id}")
    print(f"Создано пользователем: {inv.employee.username}")
    print(f"Гость: {inv.guest_full_name}")
    print(f"ИИН: {getattr(inv, 'guest_iin', 'Не указан')}")
    print(f"Заполнено: {inv.is_filled}")
    print(f"Зарегистрировано: {inv.is_registered}")
    print(f"Дата создания: {inv.created_at}")
    print("-" * 50)

print("\n=== Проверка для пользователя sagat.akimbay ===")
try:
    user_sagat = User.objects.get(username='sagat.akimbay')
    user_invitations = GuestInvitation.objects.filter(
        employee=user_sagat,
        is_filled=True,
        is_registered=False
    )
    print(f"Приглашений для sagat.akimbay: {user_invitations.count()}")
    for inv in user_invitations:
        print(f"- {inv.guest_full_name} (создано: {inv.created_at})")
except User.DoesNotExist:
    print("Пользователь sagat.akimbay не найден")
