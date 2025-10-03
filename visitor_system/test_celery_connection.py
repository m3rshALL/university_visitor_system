"""Test Celery connection from local Django to Docker Celery worker"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from django.conf import settings
from celery import chain
from hikvision_integration.tasks import enroll_face_task, assign_access_level_task

print("=" * 60)
print("CELERY CONNECTION TEST")
print("=" * 60)
print(f"Settings module: {settings.SETTINGS_MODULE}")
print(f"CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
print(f"CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}")
print(f"REDIS_HOST env: {os.environ.get('REDIS_HOST', 'NOT SET')}")
print("=" * 60)

# Test sending a chain task
print("\nSending test Celery chain...")
try:
    result = chain(
        enroll_face_task.s(3),  # HikAccessTask ID 3
        assign_access_level_task.si(4)  # HikAccessTask ID 4
    ).apply_async()
    print(f"✅ Task sent successfully!")
    print(f"Result ID: {result.id}")
    print(f"\nNow check celery-worker logs:")
    print(f"  docker-compose logs -f celery-worker | Select-String 'enroll_face|assign_access'")
except Exception as e:
    print(f"❌ Failed to send task: {e}")
    import traceback
    traceback.print_exc()
