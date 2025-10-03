"""Debug: check if tasks are being received by worker"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from django.conf import settings
from hikvision_integration.tasks import enroll_face_task

print("=" * 60)
print("DEBUGGING CELERY TASK DELIVERY")
print("=" * 60)
print(f"CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
print("=" * 60)

# Send a simple task
print("\n1. Sending single enroll_face_task...")
result = enroll_face_task.delay(999)  # Fake task ID
print(f"   Task ID: {result.id}")
print(f"   Task sent!")

print("\n2. Waiting 3 seconds for task to be processed...")
time.sleep(3)

print("\n3. Checking task result...")
try:
    status = result.status
    print(f"   Status: {status}")
    
    if status == 'SUCCESS':
        print(f"   ✅ Task completed successfully!")
        print(f"   Result: {result.result}")
    elif status == 'FAILURE':
        print(f"   ❌ Task failed!")
        print(f"   Error: {result.info}")
    elif status == 'PENDING':
        print(f"   ⏳ Task still pending (worker may not be receiving it)")
    else:
        print(f"   Status: {status}")
except Exception as e:
    print(f"   Error checking status: {e}")

print("\n" + "=" * 60)
print("CHECK THE CELERY WORKER WINDOW:")
print("You should see: [INFO] Task hikvision_integration.tasks.enroll_face_task[...] received")
print("=" * 60)
