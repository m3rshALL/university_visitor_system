"""
Ручной запуск задачи мониторинга проходов гостей.
Полезно для тестирования без запуска Celery Beat.
"""

import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from hikvision_integration.tasks import monitor_guest_passages_task


if __name__ == '__main__':
    print("\n" + "="*80)
    print("РУЧНОЙ ЗАПУСК ЗАДАЧИ МОНИТОРИНГА")
    print("="*80 + "\n")
    
    print("🚀 Запуск monitor_guest_passages_task()...")
    
    try:
        monitor_guest_passages_task()
        print("\n✅ Задача выполнена успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка выполнения задачи: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ ЗАВЕРШЕНО")
    print("="*80 + "\n")
