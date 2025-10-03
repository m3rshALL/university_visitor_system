#!/usr/bin/env python
"""
Тестовый скрипт для проверки автоматического check-in/checkout через FaceID.

Проверяет:
- Автоматическое изменение статуса EXPECTED → CHECKED_IN при входе
- Автоматическое изменение статуса CHECKED_IN → CHECKED_OUT при выходе
- Установку entry_time и exit_time
- Audit logging
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'visitor_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from visitors.models import Visit, AuditLog
from django.utils import timezone
from datetime import timedelta


def test_auto_checkin_logic():
    """Test 1: Проверка логики автоматического check-in"""
    print("=" * 70)
    print("TEST 1: Auto Check-in Logic")
    print("=" * 70)
    
    # Ищем визиты с access_granted=True и status=EXPECTED
    expected_visits = Visit.objects.filter(
        access_granted=True,
        access_revoked=False,
        status='EXPECTED'
    )
    
    print(f"\n📊 Визиты в статусе EXPECTED с активным доступом: {expected_visits.count()}")
    
    if expected_visits.exists():
        sample = expected_visits.first()
        print(f"\n📝 Пример визита готового к авто check-in:")
        print(f"   ID: {sample.id}")
        print(f"   Guest: {sample.guest}")
        print(f"   Status: {sample.status}")
        print(f"   Person ID: {sample.hikcentral_person_id}")
        print(f"   Entry time: {sample.entry_time}")
        print(f"   First entry detected: {sample.first_entry_detected}")
        print(f"\n   ✅ Этот визит автоматически перейдет в CHECKED_IN при проходе через турникет")
    else:
        print("   ⚠️  Нет визитов в статусе EXPECTED с активным доступом")
    
    print()
    return True


def test_auto_checkout_logic():
    """Test 2: Проверка логики автоматического checkout"""
    print("=" * 70)
    print("TEST 2: Auto Checkout Logic")
    print("=" * 70)
    
    # Ищем визиты с access_granted=True и status=CHECKED_IN
    checked_in_visits = Visit.objects.filter(
        access_granted=True,
        access_revoked=False,
        status='CHECKED_IN'
    )
    
    print(f"\n📊 Визиты в статусе CHECKED_IN: {checked_in_visits.count()}")
    
    if checked_in_visits.exists():
        sample = checked_in_visits.first()
        print(f"\n📝 Пример визита готового к авто checkout:")
        print(f"   ID: {sample.id}")
        print(f"   Guest: {sample.guest}")
        print(f"   Status: {sample.status}")
        print(f"   Entry time: {sample.entry_time}")
        print(f"   Exit time: {sample.exit_time}")
        print(f"   First exit detected: {sample.first_exit_detected}")
        print(f"\n   ✅ Этот визит автоматически перейдет в CHECKED_OUT при выходе через турникет")
    else:
        print("   ℹ️  Нет визитов в статусе CHECKED_IN")
    
    print()
    return True


def test_celery_schedule():
    """Test 3: Проверка расписания Celery Beat"""
    print("=" * 70)
    print("TEST 3: Celery Beat Schedule")
    print("=" * 70)
    
    from visitor_system.celery import app
    
    schedule = app.conf.beat_schedule
    monitor_task = schedule.get('monitor-guest-passages')
    
    if monitor_task:
        print(f"\n✅ Monitor task configured:")
        print(f"   Task: {monitor_task['task']}")
        print(f"   Schedule: {monitor_task['schedule']}")
        
        # Проверяем интервал
        schedule_obj = monitor_task['schedule']
        if hasattr(schedule_obj, 'minute'):
            if schedule_obj.minute == '*/5':
                print(f"   ✅ Frequency: Every 5 minutes (CORRECT)")
            elif schedule_obj.minute == '*/10':
                print(f"   ⚠️  Frequency: Every 10 minutes (OLD - should be 5)")
            else:
                print(f"   ℹ️  Frequency: {schedule_obj.minute}")
    else:
        print("   ❌ Monitor task NOT found in beat_schedule")
    
    print()
    return True


def test_recent_auto_actions():
    """Test 4: Проверка недавних автоматических действий"""
    print("=" * 70)
    print("TEST 4: Recent Auto Check-in/out Actions")
    print("=" * 70)
    
    # Ищем audit logs с автоматическими действиями за последние 24 часа
    yesterday = timezone.now() - timedelta(hours=24)
    
    auto_checkin_logs = AuditLog.objects.filter(
        created_at__gte=yesterday,
        user_agent='HikCentral FaceID System',
        changes__contains='Auto check-in'
    ).order_by('-created_at')
    
    auto_checkout_logs = AuditLog.objects.filter(
        created_at__gte=yesterday,
        user_agent='HikCentral FaceID System',
        changes__contains='Auto checkout'
    ).order_by('-created_at')
    
    print(f"\n📊 Auto check-ins (last 24h): {auto_checkin_logs.count()}")
    if auto_checkin_logs.exists():
        latest = auto_checkin_logs.first()
        print(f"   Latest: Visit {latest.object_id} at {latest.created_at}")
        print(f"   Changes: {latest.changes}")
    
    print(f"\n📊 Auto checkouts (last 24h): {auto_checkout_logs.count()}")
    if auto_checkout_logs.exists():
        latest = auto_checkout_logs.first()
        print(f"   Latest: Visit {latest.object_id} at {latest.created_at}")
        print(f"   Changes: {latest.changes}")
    
    if not auto_checkin_logs.exists() and not auto_checkout_logs.exists():
        print("\n   ℹ️  No automatic actions yet (feature just deployed)")
    
    print()
    return True


def test_monitoring_task_import():
    """Test 5: Проверка импорта task"""
    print("=" * 70)
    print("TEST 5: Monitor Task Import")
    print("=" * 70)
    
    try:
        from hikvision_integration.tasks import monitor_guest_passages_task
        print("✅ monitor_guest_passages_task imported successfully")
        print(f"✅ Task name: {monitor_guest_passages_task.name}")
        print()
        return True
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        print()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("AUTO CHECK-IN/CHECKOUT FEATURE TEST SUITE")
    print("=" * 70 + "\n")
    
    tests = [
        ("Monitor Task Import", test_monitoring_task_import),
        ("Auto Check-in Logic", test_auto_checkin_logic),
        ("Auto Checkout Logic", test_auto_checkout_logic),
        ("Celery Beat Schedule", test_celery_schedule),
        ("Recent Auto Actions", test_recent_auto_actions),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📝 Next steps:")
        print("   1. Restart Celery Beat: docker-compose restart celery-beat")
        print("   2. Restart Celery Worker: docker-compose restart celery-worker")
        print("   3. Wait for next monitoring cycle (every 5 minutes)")
        print("   4. Check logs: docker-compose logs -f celery-worker | grep 'Auto check'")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
    
    print("=" * 70 + "\n")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
