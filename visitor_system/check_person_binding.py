#!/usr/bin/env python
"""Проверка HikPersonBinding для guest 211."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.models import HikPersonBinding

b = HikPersonBinding.objects.filter(guest_id=211).first()
print(f'Binding exists: {bool(b)}')

if b:
    print(f'  person_id: {b.person_id}')
    print(f'  face_id: {b.face_id}')
    print(f'  status: {b.status}')
else:
    print('  NO BINDING FOUND!')
