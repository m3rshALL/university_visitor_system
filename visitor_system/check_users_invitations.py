#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from visitors.models import GuestInvitation
from django.contrib.auth.models import User

print('=== ВСЕ ПОЛЬЗОВАТЕЛИ ===')
users = User.objects.all()
for user in users:
    print(f'- {user.username} | {user.get_full_name()} | is_staff: {user.is_staff}')

print('\n=== ЗАПОЛНЕННЫЕ ПРИГЛАШЕНИЯ ===')
pending = GuestInvitation.objects.filter(is_filled=True, is_registered=False)
print(f'Заполненных приглашений: {pending.count()}')

for inv in pending:
    print(f'- {inv.guest_full_name} | employee: {inv.employee.username} | created: {inv.created_at}')

print('\n=== ПРОВЕРИМ КОНКРЕТНЫХ ПОЛЬЗОВАТЕЛЕЙ ===')
# Проверяем пользователей, у которых есть приглашения
for username in ['sagat.akimbay', 'sako']:
    try:
        user = User.objects.get(username=username)
        user_pending = GuestInvitation.objects.filter(
            employee=user,
            is_filled=True, 
            is_registered=False
        )
        print(f'Заполненных приглашений для {user.username}: {user_pending.count()}')
        for inv in user_pending:
            print(f'  - {inv.guest_full_name} | created: {inv.created_at}')
    except User.DoesNotExist:
        print(f'Пользователь {username} не найден')
