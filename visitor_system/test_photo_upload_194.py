#!/usr/bin/env python
"""Test photo upload manually for Visit 194."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.tasks import enroll_face_task
from hikvision_integration.models import HikAccessTask

# Найдем task 62 (enroll_face для Visit 194)
task = HikAccessTask.objects.get(id=62)

print(f"Task 62 details:")
print(f"  kind: {task.kind}")
print(f"  status: {task.status}")
print(f"  visit_id: {task.visit_id}")
print(f"  guest_id: {task.guest_id}")
print(f"  last_error: {task.last_error}")

print("\nRetrying enroll_face_task for task 62...")
print("Watch logs: celery_hikvision.log and celery_hikvision_error.log")

result = enroll_face_task.apply_async(args=[62], queue='hikvision')
print(f"\n✅ Task resent: {result.id}")
