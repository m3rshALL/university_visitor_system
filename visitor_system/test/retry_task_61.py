#!/usr/bin/env python
"""Quick script to retry HikAccessTask 61 (assign_access_level_task)."""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.tasks import assign_access_level_task

if __name__ == '__main__':
    print("Retrying task 61 (assign_access_level_task)...")
    result = assign_access_level_task.apply_async(args=[61], queue='hikvision')
    print(f"✅ Task resent: {result.id}")
    print("Monitor logs: celery_hikvision_error.log")
