#!/usr/bin/env python
import os
import django

from visitors.models import GuestInvitation
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

print('=== ВСЕ ПРИГЛАШЕНИЯ ===')
all_invitations = GuestInvitation.objects.all()
print(f'Всего приглашений: {all_invitations.count()}')

for inv in all_invitations:
    print(f'- {inv.guest_full_name or "Не заполнено"} | is_filled: '
          f'{inv.is_filled} | is_registered: {inv.is_registered} | '
          f'employee: {inv.employee.username}')

print('\n=== ЗАПОЛНЕННЫЕ ПРИГЛАШЕНИЯ ===')
pending = GuestInvitation.objects.filter(is_filled=True, is_registered=False)
print(f'Заполненных приглашений: {pending.count()}')

for inv in pending:
    print(f'- {inv.guest_full_name} | employee: {inv.employee.username} | '
          f'created: {inv.created_at}')

print('\n=== ПРОВЕРИМ КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ===')
try:
    user = User.objects.get(username='admin')  # или другой username
    user_pending = GuestInvitation.objects.filter(
        employee=user,
        is_filled=True,
        is_registered=False
    )
    print(f'Заполненных приглашений для {user.username}: {user_pending.count()}')
    for inv in user_pending:
        print(f'  - {inv.guest_full_name} | created: {inv.created_at}')
except User.DoesNotExist:
    print('Пользователь admin не найден')
