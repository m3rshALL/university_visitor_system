#!/usr/bin/env python
"""Проверка последнего гостя и наличия фото."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from visitors.models import Visit, GuestInvitation

v = Visit.objects.select_related('guest').order_by('-id').first()
print(f'Visit {v.id}: guest={v.guest.full_name if v.guest else None}')

inv = GuestInvitation.objects.filter(visit=v).first()
print(f'Has invitation: {bool(inv)}')

if inv:
    print(f'  has guest_photo: {bool(inv.guest_photo)}')
    if inv.guest_photo:
        print(f'  photo path: {inv.guest_photo.path}')
        import os
        print(f'  file exists: {os.path.exists(inv.guest_photo.path)}')
