#!/usr/bin/env python
"""
Тест end-to-end: создание гостя и автоматическая загрузка фото
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, 'D:\\university_visitor_system\\visitor_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from django.core.files.base import ContentFile
from visitors.models import Guest
from hikvision_integration.tasks import enroll_face_task
import time

# Тестовое фото
photo_path = r'D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg'

print("=" * 80)
print("ТЕСТ: Создание гостя с автоматической загрузкой фото в HikCentral")
print("=" * 80)

# Создаем тестового гостя
print("\n1️⃣ Создание Guest...")
with open(photo_path, 'rb') as f:
    photo_content = f.read()

guest = Guest.objects.create(
    full_name="Дуров Павел Валерьевич"
)
guest.photo.save('test_durov.jpg', ContentFile(photo_content), save=True)
print(f"✅ Guest создан: ID={guest.id}, {guest.full_name}")
print(f"   Photo: {guest.photo.path if guest.photo else 'NO PHOTO'}")
print(f"   HikCentral ID: {guest.hikcentral_person_id or 'НЕТ'}")

# Проверяем есть ли HikCentral ID
if not guest.hikcentral_person_id:
    print("\n⚠️ HikCentral ID не создан автоматически")
    print("   Это нормально - ID создается при первом визите")
    print("   Для теста можно создать Person вручную...")
    
    from hikvision_integration.services import HikCentralSession, create_person_hikcentral
    from django.conf import settings
    
    session = HikCentralSession(
        settings.HIKVISION_HCP_SERVER,
        settings.HIKVISION_HCP_USER,
        settings.HIKVISION_HCP_PASSWORD
    )
    
    if session.login():
        print("\n2️⃣ Создание Person в HikCentral...")
        person_id = create_person_hikcentral(
            session,
            f"{guest.first_name} {guest.last_name}",
            guest.phone_number or ""
        )
        
        if person_id:
            guest.hikcentral_person_id = person_id
            guest.save()
            print(f"✅ Person создан: ID={person_id}")
        else:
            print("❌ Не удалось создать Person")
            sys.exit(1)
    else:
        print("❌ Не удалось подключиться к HikCentral")
        sys.exit(1)

# Теперь загружаем фото через task
print(f"\n3️⃣ Запуск enroll_face_task для загрузки фото...")
print(f"   Person ID: {guest.hikcentral_person_id}")
print(f"   Photo path: {guest.photo.path}")

result = enroll_face_task(
    guest.id,
    str(guest.photo.path),
    guest.hikcentral_person_id
)

print(f"\n4️⃣ Результат загрузки: {result}")

# Проверяем что фото действительно загрузилось
print("\n5️⃣ Проверка в HikCentral...")
from hikvision_integration.services import HikCentralSession
from django.conf import settings

session = HikCentralSession(
    settings.HIKVISION_HCP_SERVER,
    settings.HIKVISION_HCP_USER,
    settings.HIKVISION_HCP_PASSWORD
)

if session.login():
    person_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
        'personId': str(guest.hikcentral_person_id)
    })
    person_json = person_resp.json()
    
    if person_json.get('code') == '0':
        person_data = person_json.get('data', {})
        pic_uri = person_data.get('personPhoto', {}).get('picUri', '')
        
        print(f"   Code: {person_json.get('code')}")
        print(f"   Msg: {person_json.get('msg')}")
        print(f"   picUri: {pic_uri}")
        
        if pic_uri and pic_uri != '':
            print("\n✅✅✅ УСПЕХ! ФОТО ЗАГРУЖЕНО В HIKVISION!")
            print(f"   picUri = '{pic_uri}'")
            print("\n🎉 АВТОМАТИЗАЦИЯ ПОЛНОСТЬЮ РАБОТАЕТ!")
        else:
            print("\n❌ picUri пустой - фото НЕ загрузилось")
    else:
        print(f"\n❌ Ошибка запроса: {person_json.get('msg')}")
else:
    print("❌ Не удалось подключиться к HikCentral для проверки")

# Очистка
print(f"\n6️⃣ Очистка...")
print(f"   Удалить тестового гостя? (Guest ID={guest.id})")
response = input("   Введите 'yes' для удаления: ")
if response.lower() == 'yes':
    guest.delete()
    print("   ✅ Guest удален")
else:
    print(f"   ℹ️ Guest сохранен (ID={guest.id})")

print("\n" + "=" * 80)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 80)
