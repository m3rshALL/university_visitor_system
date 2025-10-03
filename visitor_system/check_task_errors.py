#!/usr/bin/env python
"""Проверка ошибок задач для visit 193."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.models import HikAccessTask

tasks = HikAccessTask.objects.filter(visit_id=193).order_by('id')

for t in tasks:
    print(f'{t.id}: {t.kind} - {t.status}')
    if t.last_error:
        print(f'  Error: {t.last_error}')
