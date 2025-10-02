"""
Создание тестового визита с полным циклом доступа для проверки мониторинга.

Шаги:
1. Создаёт Guest в Django
2. Создаёт Visit в Django
3. Создаёт person в HikCentral
4. Загружает фото
5. Назначает access level
6. Помечает visit.access_granted=True
"""

import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from django.utils import timezone
from datetime import timedelta, datetime
from visitors.models import Guest, Visit, EmployeeProfile
from hikvision_integration.services import (
    HikCentralSession,
    ensure_person_hikcentral,
    upload_face_hikcentral,
    assign_access_level_to_person
)
from django.conf import settings


def create_test_visit_with_access():
    """Создаёт тестовый визит с доступом"""
    
    print("\n" + "="*80)
    print("СОЗДАНИЕ ТЕСТОВОГО ВИЗИТА С ДОСТУПОМ")
    print("="*80 + "\n")
    
    # 1. Создаём Guest в Django (если нет)
    print("1️⃣ Создание гостя в Django...")
    
    # Используем timestamp для уникальности
    timestamp = int(datetime.now().timestamp())
    
    guest, created = Guest.objects.get_or_create(
        full_name=f"Test Monitoring {timestamp}",
        defaults={
            'email': f'test.monitoring{timestamp}@example.com',
            'phone_number': '+77001112233',
        }
    )
    
    if created:
        print(f"✅ Guest создан: {guest.full_name} (ID={guest.id})")
    else:
        print(f"✅ Guest найден: {guest.full_name} (ID={guest.id})")
    
    # 2. Находим Employee для визита
    print("\n2️⃣ Поиск Employee для визита...")
    
    from django.contrib.auth.models import User
    
    user = User.objects.filter(is_active=True, is_staff=True).first()
    if not user:
        print("❌ Нет активных пользователей в системе")
        return
    
    print(f"✅ User найден: {user.get_full_name()} (ID={user.id})")
    
    # 3. Создаём Visit
    print("\n3️⃣ Создание визита в Django...")
    
    from departments.models import Department
    
    # Находим любой департамент
    department = Department.objects.first()
    if not department:
        print("❌ Нет департаментов в системе")
        return
    
    now = timezone.now()
    
    visit, created = Visit.objects.get_or_create(
        guest=guest,
        employee=user,
        defaults={
            'purpose': 'Тест мониторинга проходов',
            'department': department,
            'registered_by': user,
            'expected_entry_time': now,
            'status': 'EXPECTED',
        }
    )
    
    if created:
        print(f"✅ Visit создан (ID={visit.id})")
    else:
        print(f"✅ Visit найден (ID={visit.id})")
    
    # 4. Подключаемся к HikCentral
    print("\n4️⃣ Подключение к HikCentral...")
    
    from hikvision_integration.models import HikCentralServer
    
    server = HikCentralServer.objects.filter(enabled=True).first()
    if not server:
        print("❌ HikCentral Server не настроен")
        return
    
    session = HikCentralSession(server)
    
    print("✅ Подключено к HikCentral")
    
    # 5. Создаём person в HikCentral
    print("\n5️⃣ Создание person в HikCentral...")
    
    # Используем timestamp как employee_no для уникальности
    employee_no = str(timestamp)
    
    person_id = ensure_person_hikcentral(
        session,
        employee_no=employee_no,
        name=guest.full_name,
        valid_from=now.isoformat(),
        valid_to=(now.replace(hour=22, minute=0, second=0)).isoformat()
    )
    
    if not person_id:
        print("❌ Не удалось создать person в HikCentral")
        return
    
    print(f"✅ Person создан: ID={person_id}, Employee No={employee_no}")
    
    # Сохраняем person_id в Visit
    visit.hikcentral_person_id = person_id
    visit.save(update_fields=['hikcentral_person_id'])
    print(f"   ✅ Person ID сохранён в Visit")
    
    # 6. Загружаем фото
    print("\n6️⃣ Загрузка фото...")
    
    # Используем дефолтное фото для теста
    photo_path = os.path.join(
        os.path.dirname(__file__),
        'test_photos',
        'test_face.jpg'
    )
    
    if not os.path.exists(photo_path):
        print(f"⚠️  Фото не найдено: {photo_path}")
        print("   Пропускаем загрузку фото...")
    else:
        result = upload_face_hikcentral(session, person_id, photo_path)
        
        if result and result.get('code') == 0:
            print(f"✅ Фото загружено: picUri={result.get('data', {}).get('picUri', 'N/A')}")
        else:
            print(f"⚠️  Не удалось загрузить фото: {result}")
    
    # 7. Назначаем access level
    print("\n7️⃣ Назначение access level...")
    
    access_group_id = getattr(settings, 'HIKCENTRAL_GUEST_ACCESS_GROUP_ID', '7')
    
    success = assign_access_level_to_person(
        session,
        str(person_id),
        str(access_group_id),
        access_type=1
    )
    
    if not success:
        print("❌ Не удалось назначить access level")
        return
    
    print(f"✅ Access level назначен (group_id={access_group_id})")
    
    # 8. Помечаем visit.access_granted=True
    print("\n8️⃣ Обновление статуса визита...")
    
    visit.access_granted = True
    visit.status = 'CHECKED_IN'
    visit.save(update_fields=['access_granted', 'status'])
    
    print(f"✅ Visit.access_granted = True")
    
    # Итоговая информация
    print("\n" + "="*80)
    print("✅ ТЕСТОВЫЙ ВИЗИТ СОЗДАН УСПЕШНО!")
    print("="*80)
    print(f"\n📋 Детали:")
    print(f"   Guest ID: {guest.id}")
    print(f"   Visit ID: {visit.id}")
    print(f"   HikCentral Person ID: {person_id}")
    print(f"   Employee No: {employee_no}")
    print(f"   Access Group ID: {access_group_id}")
    print(f"\n💡 Теперь можно:")
    print(f"   1. Проверить мониторинг: poetry run python test_monitoring_task.py")
    print(f"   2. Запустить задачу вручную: poetry run python test_run_monitoring_task.py")
    print(f"   3. Пропустить гостя через турникет и проверить автоблокировку")
    print()


if __name__ == '__main__':
    create_test_visit_with_access()
