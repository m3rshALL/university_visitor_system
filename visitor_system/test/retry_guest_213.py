#!/usr/bin/env python
"""Retry photo upload for Guest 213 (Visit 195, Task 64)."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.tasks import enroll_face_task
from hikvision_integration.models import HikAccessTask, HikPersonBinding

# Task 64 - enroll_face для Visit 195 (Guest 213)
task = HikAccessTask.objects.get(id=64)

print("=" * 60)
print("RETRY PHOTO UPLOAD FOR GUEST 213")
print("=" * 60)
print(f"Task ID: {task.id}")
print(f"Kind: {task.kind}")
print(f"Status: {task.status}")
print(f"Visit ID: {task.visit_id}")
print(f"Guest ID: {task.guest_id}")
print(f"Last error: {task.last_error[:100] if task.last_error else 'None'}")

# Проверяем current binding
binding = HikPersonBinding.objects.filter(guest_id=213).first()
if binding:
    print(f"\nCurrent binding:")
    print(f"  person_id: {binding.person_id}")
    print(f"  face_id: {binding.face_id}")
    print(f"  status: {binding.status}")
    print(f"  updated_at: {binding.updated_at}")

print("\n" + "=" * 60)
print("SENDING TASK TO CELERY...")
print("=" * 60)
print("Watch logs: celery_hikvision_error.log")
print("Expected to see:")
print("  - 'Sending payload with personId=...'")
print("  - 'person/face/update response code=...'")
print("  - If code=0: SUCCESS! ✅")
print("  - If code!=0: Check error message")
print("=" * 60)

result = enroll_face_task.apply_async(args=[64], queue='hikvision')
print(f"\n✅ Task resent with ID: {result.id}")
print("\nWait 15 seconds then check binding:")
print("  poetry run python -c \"import os, sys, django; ...")
