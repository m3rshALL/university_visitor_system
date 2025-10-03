#!/usr/bin/env python
"""
Простой тест: проверка работы Celery worker с HikCentral задачами.
"""
import os
import sys
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.models import HikAccessTask
from hikvision_integration.tasks import enroll_face_task

def test_celery_task():
    """Отправляем тестовую задачу и проверяем выполнение."""
    print("=" * 70)
    print("ТЕСТ: Celery Worker + HikCentral задачи")
    print("=" * 70)
    
    # 1. Создаем тестовую HikAccessTask
    print("\n📝 Создаем тестовую HikAccessTask...")
    task = HikAccessTask.objects.create(
        kind='enroll_face',
        status='queued'
    )
    print(f"✅ Task created: ID={task.id}, Status={task.status}")
    
    # 2. Отправляем задачу в Celery
    print(f"\n📤 Отправляем задачу в Celery (queue=hikvision)...")
    result = enroll_face_task.apply_async(args=[task.id], queue='hikvision')
    print(f"✅ Task sent: {result.id}")
    
    # 3. Ждем выполнения
    print(f"\n⏳ Ожидаем выполнение (max 10 секунд)...")
    max_wait = 10
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        task.refresh_from_db()
        print(f"   Status: {task.status}")
        
        if task.status in ['completed', 'failed']:
            break
        
        time.sleep(1)
    
    # 4. Проверяем результат
    task.refresh_from_db()
    print(f"\n📊 Финальный статус: {task.status}")
    
    if task.error_message:
        print(f"   Error: {task.error_message}")
    
    # 5. Итог
    print("\n" + "=" * 70)
    if task.status == 'completed':
        print("🎉 УСПЕХ! Задача выполнена")
        return True
    elif task.status == 'failed':
        print("⚠️ Задача завершилась с ошибкой (это ожидаемо для тестовой задачи)")
        print("   Главное что worker ПОЛУЧИЛ и ОБРАБОТАЛ задачу!")
        return True
    else:
        print("❌ ОШИБКА! Задача не была обработана")
        print("   Проверьте что Celery worker запущен:")
        print("   cd d:\\university_visitor_system && start_celery.bat")
        return False
    
    print("=" * 70)

if __name__ == "__main__":
    try:
        success = test_celery_task()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
