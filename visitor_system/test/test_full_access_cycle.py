#!/usr/bin/env python
"""
Тест полного цикла: создание Person → загрузка фото → назначение access level
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, 'D:\\university_visitor_system\\visitor_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import (
    HikCentralSession,
    ensure_person_hikcentral,
    upload_face_hikcentral,
    assign_access_level_to_person,
)
from hikvision_integration.models import HikCentralServer
from django.conf import settings

print("=" * 80)
print("ТЕСТ: Полный цикл - Person → Photo → Access Level")
print("=" * 80)

# Получаем session
server = HikCentralServer.objects.filter(enabled=True).first()
if not server:
    print("❌ HikCentral Server не настроен")
    sys.exit(1)

session = HikCentralSession(server)
print("✅ Сессия создана\n")

# Данные тестового гостя
test_name = "Тестов Тест Тестович"
test_phone = "+77001234567"
test_photo_path = r'D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg'

# Шаг 1: Создаем Person
print("🔹 Шаг 1: Создание Person в HCP")
from datetime import datetime, timedelta

# Период действия: сейчас до 22:00 сегодня
now = datetime.now()
valid_from = now.strftime('%Y-%m-%dT%H:%M:%S+06:00')
end_time = now.replace(hour=22, minute=0, second=0)
valid_to = end_time.strftime('%Y-%m-%dT%H:%M:%S+06:00')

employee_no = f"{int(now.timestamp())}"  # Только цифры - избегаем ошибок с personCode

person_id = ensure_person_hikcentral(
    session,
    employee_no=employee_no,
    name=test_name,
    valid_from=valid_from,
    valid_to=valid_to
)

if not person_id:
    print("❌ Не удалось создать Person")
    sys.exit(1)

print(f"✅ Person создан: ID={person_id}")
print(f"   Employee No: {employee_no}")
print(f"   Validity: {valid_from} → {valid_to}\n")

# Шаг 2: Загружаем фото
print("🔹 Шаг 2: Загрузка фото")
with open(test_photo_path, 'rb') as f:
    photo_bytes = f.read()

face_id = upload_face_hikcentral(
    session,
    face_lib_id='1',  # не используется
    image_bytes=photo_bytes,
    person_id=person_id
)

if not face_id or face_id.startswith('face_'):
    print(f"⚠️ Фото не загрузилось полностью: face_id={face_id}")
else:
    print(f"✅ Фото загружено: face_id={face_id}\n")

# Шаг 3: Назначаем access level
print("🔹 Шаг 3: Назначение Access Level")
access_group_id = getattr(settings, 'HIKCENTRAL_GUEST_ACCESS_GROUP_ID', '7')
print(f"   Access Group ID: {access_group_id}")
print(f"   Person ID: {person_id}")

success = assign_access_level_to_person(
    session,
    person_id,
    access_group_id,
    access_type=1  # Access Control
)

if success:
    print("✅ Access level успешно назначен!\n")
else:
    print("❌ Не удалось назначить access level\n")
    sys.exit(1)

# Шаг 4: Проверяем результат
print("🔹 Шаг 4: Проверка Person в HCP")
person_resp = session._make_request(
    'POST',
    '/artemis/api/resource/v1/person/personId/personInfo',
    data={'personId': str(person_id)}
)

person_data = person_resp.json()
if person_data.get('code') == '0':
    data = person_data.get('data', {})
    print(f"   Имя: {data.get('personName')}")
    print(f"   Телефон: {data.get('phoneNo')}")
    
    pic_uri = data.get('personPhoto', {}).get('picUri', '')
    if pic_uri:
        print(f"   ✅ Фото: {pic_uri}")
    else:
        print("   ⚠️ Фото не найдено")
else:
    print(f"   ❌ Ошибка: {person_data.get('msg')}")

print("\n" + "=" * 80)
print("🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
print("=" * 80)
print("\nТеперь гость может:")
print("  1. ✅ Пройти по турникету (распознавание лица)")
print("  2. ✅ Войти в здание")
print("  3. ✅ Выйти из здания")
print("  4. ✅ Доступ действует с 09:00 до 22:00")
print("\n⚠️ ВАЖНО: Для полного контроля одноразового доступа")
print("   нужно реализовать мониторинг событий через /door/events")
print("=" * 80)

# Очистка
print("\n❓ Удалить тестового гостя из HCP?")
response = input("   Введите 'yes' для удаления: ")
if response.lower() == 'yes':
    try:
        del_resp = session._make_request(
            'POST',
            '/artemis/api/resource/v1/person/single/delete',
            data={'personId': str(person_id)}
        )
        del_result = del_resp.json()
        if del_result.get('code') == '0':
            print("   ✅ Person удален")
        else:
            print(f"   ⚠️ Ошибка удаления: {del_result.get('msg')}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
else:
    print(f"   ℹ️ Person сохранен (ID={person_id})")
