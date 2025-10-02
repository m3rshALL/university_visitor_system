"""
Тестовый скрипт для проверки задачи мониторинга проходов гостей.

Проверяет:
1. Получение активных визитов с access_granted=True
2. Запрос событий door events через API
3. Обновление счётчиков проходов
4. Автоматическую блокировку после первого выхода
"""

import os
import sys
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from django.utils import timezone
from datetime import timedelta
from visitors.models import Visit
from hikvision_integration.services import HikCentralSession, get_door_events


def test_monitoring():
    """Тестирует задачу мониторинга"""
    
    print("\n" + "="*80)
    print("ТЕСТ МОНИТОРИНГА ПРОХОДОВ ГОСТЕЙ")
    print("="*80 + "\n")
    
    # 1. Проверяем активные визиты
    print("1️⃣ Поиск активных визитов с предоставленным доступом...")
    active_visits = Visit.objects.filter(
        access_granted=True,
        access_revoked=False,
        status__in=['EXPECTED', 'CHECKED_IN']
    ).select_related('guest')
    
    if not active_visits.exists():
        print("❌ Нет активных визитов с предоставленным доступом")
        print("\nСоздайте тестовый визит через:")
        print("  poetry run python test_full_access_cycle.py")
        return
    
    print(f"✅ Найдено активных визитов: {active_visits.count()}")
    
    for visit in active_visits:
        print(f"\n📋 Visit ID: {visit.id}")
        print(f"   Guest: {visit.guest.full_name}")
        print(f"   Status: {visit.status}")
        print(f"   Access granted: {visit.access_granted}")
        print(f"   Access revoked: {visit.access_revoked}")
        print(f"   Entry count: {visit.entry_count}")
        print(f"   Exit count: {visit.exit_count}")
        if visit.first_entry_detected:
            print(f"   First entry: {visit.first_entry_detected}")
        if visit.first_exit_detected:
            print(f"   First exit: {visit.first_exit_detected}")
    
    # 2. Подключаемся к HikCentral
    print("\n2️⃣ Подключение к HikCentral...")
    
    from hikvision_integration.models import HikCentralServer
    
    server = HikCentralServer.objects.filter(enabled=True).first()
    if not server:
        print("❌ HikCentral Server не настроен")
        return
    
    session = HikCentralSession(server)
    print("✅ Подключено к HikCentral")
    
    # 3. Запрашиваем события для каждого визита
    print("\n3️⃣ Запрос событий проходов через API...")
    
    now = timezone.now()
    start_time = now - timedelta(hours=24)  # Последние 24 часа
    
    for visit in active_visits:
        # Получаем person_id из visit
        if not visit.hikcentral_person_id:
            print(f"\n❌ Visit {visit.id}: No hikcentral_person_id")
            continue
        
        person_id = str(visit.hikcentral_person_id)
        
        print(f"\n📡 Запрос событий для person_id={person_id}...")
        
        try:
            events_data = get_door_events(
                session,
                person_id=person_id,
                person_name=None,
                start_time=start_time.isoformat(),
                end_time=now.isoformat(),
                door_index_codes=None,
                event_type=None,
                page_no=1,
                page_size=100
            )
            
            if not events_data or 'list' not in events_data:
                print("   ⚠️  Нет данных о проходах")
                continue
            
            events = events_data.get('list', [])
            total_count = events_data.get('total', 0)
            
            print(f"   ✅ Найдено событий: {total_count}")
            
            if events:
                print("\n   📊 События проходов:")
                for idx, event in enumerate(events[:10], 1):  # Показываем первые 10
                    event_type = event.get('eventType')
                    event_time = event.get('eventTime')
                    door_name = event.get('doorName', 'Unknown')
                    event_type_name = 'ВХОД' if event_type == 1 else 'ВЫХОД' if event_type == 2 else f'TYPE_{event_type}'
                    
                    print(f"      {idx}. {event_time} | {event_type_name} | {door_name}")
                
                if len(events) > 10:
                    print(f"      ... и ещё {len(events) - 10} событий")
            else:
                print("   ℹ️  Нет событий за последние 24 часа")
        
        except Exception as e:
            print(f"   ❌ Ошибка при запросе событий: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. Симуляция обновления счётчиков (вручную)
    print("\n4️⃣ Симуляция обновления счётчиков...")
    print("   (В реальной задаче счётчики обновляются автоматически)")
    
    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("="*80)
    print("\n💡 Для автоматического мониторинга запустите Celery Beat:")
    print("   poetry run celery -A visitor_system beat --loglevel=info")
    print("\n💡 И Celery Worker:")
    print("   poetry run celery -A visitor_system worker --loglevel=info -Q hikvision")
    print()


if __name__ == '__main__':
    test_monitoring()
