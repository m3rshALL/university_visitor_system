#!/usr/bin/env python
"""
Тест полного flow регистрации гостя с HikCentral интеграцией.
Создает гостя, проверяет что задачи выполнены и гость появился в HikCentral.
"""
import os
import sys
import time
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from visitors.models import Guest, Visit
from hikvision_integration.models import HikAccessTask, HikPersonBinding

User = get_user_model()

def test_guest_registration():
    """Тестируем регистрацию гостя."""
    print("=" * 70)
    print("ТЕСТ: Полный flow регистрации гостя с HikCentral")
    print("=" * 70)
    
    # 1. Получаем или создаем сотрудника
    host_user = User.objects.filter(is_staff=True).first()
    if not host_user:
        print("❌ ERROR: Нет пользователей с is_staff=True")
        return False
    
    print(f"\n✅ Host user: {host_user.username}")
    
    # 2. Создаем гостя
    test_iin = "990101300000"  # Тестовый ИИН
    guest_name = f"Test Guest {int(time.time())}"
    
    print(f"\n📝 Создаем гостя: {guest_name}")
    print(f"   ИИН: {test_iin}")
    
    guest = Guest.objects.create(
        full_name=guest_name,
        phone_number="+77771234567",
        email="test@example.com"
    )
    # Устанавливаем ИИН через setter property
    guest.iin = test_iin
    guest.save()
    
    print(f"✅ Guest created: ID={guest.id}")
    
    # 3. Создаем визит
    visit = Visit.objects.create(
        host=host_user,
        guest=guest,
        purpose="Test Visit",
        expected_entry_time=timezone.now(),
        status='SCHEDULED'
    )
    
    print(f"✅ Visit created: ID={visit.id}, Status={visit.status}")
    
    # 4. Проверяем что создались HikAccessTask
    print("\n⏳ Ожидаем создание HikAccessTask...")
    time.sleep(1)
    
    tasks = HikAccessTask.objects.filter(visit=visit)
    print(f"✅ Found {tasks.count()} HikAccessTask records:")
    for task in tasks:
        print(f"   - Task {task.id}: {task.kind} - {task.status}")
    
    if tasks.count() == 0:
        print("❌ WARNING: HikAccessTask не созданы! Проверьте signals или views.")
        return False
    
    # 5. Ждем выполнения задач
    print("\n⏳ Ожидаем выполнение Celery задач (max 10 секунд)...")
    max_wait = 10
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        tasks = HikAccessTask.objects.filter(visit=visit)
        statuses = [t.status for t in tasks]
        
        if all(s in ['completed', 'failed'] for s in statuses):
            break
        
        print(f"   Статусы: {', '.join(statuses)}")
        time.sleep(2)
    
    # 6. Проверяем финальные статусы
    print("\n📊 Финальные статусы задач:")
    tasks = HikAccessTask.objects.filter(visit=visit)
    for task in tasks:
        print(f"   - Task {task.id}: {task.kind} - {task.status}")
        if task.error_message:
            print(f"     Error: {task.error_message}")
    
    # 7. Проверяем HikPersonBinding
    bindings = HikPersonBinding.objects.filter(guest=guest)
    print(f"\n📊 HikPersonBinding records: {bindings.count()}")
    for binding in bindings:
        print(f"   - Guest {binding.guest_id} → Person {binding.hik_person_id}")
    
    # 8. Проверяем что в Visit появился hikcentral_person_id
    visit.refresh_from_db()
    guest.refresh_from_db()
    
    print(f"\n📊 Visit {visit.id}:")
    print(f"   hikcentral_person_id: {visit.hikcentral_person_id}")
    
    print(f"\n📊 Guest {guest.id}:")
    print(f"   hikcentral_person_id: {guest.hikcentral_person_id}")
    
    # 9. Итоговый результат
    print("\n" + "=" * 70)
    success = (
        tasks.filter(status='completed').count() >= 1 and
        (visit.hikcentral_person_id or guest.hikcentral_person_id) and
        bindings.count() >= 1
    )
    
    if success:
        print("🎉 УСПЕХ! Гость зарегистрирован в HikCentral")
        print(f"   Person ID: {visit.hikcentral_person_id or guest.hikcentral_person_id}")
        print(f"   Visit ID: {visit.id}")
        print(f"   Guest ID: {guest.id}")
    else:
        print("❌ ОШИБКА! Интеграция не сработала")
        print("   Проверьте:")
        print("   1. Celery worker запущен и слушает очередь 'hikvision'")
        print("   2. HikCentral доступен и настроен")
        print("   3. Логи Celery worker для деталей ошибок")
    
    print("=" * 70)
    return success

if __name__ == "__main__":
    try:
        success = test_guest_registration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
