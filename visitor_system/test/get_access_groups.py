#!/usr/bin/env python
"""
Скрипт для получения списка Access Level Groups из HikCentral
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, 'D:\\university_visitor_system\\visitor_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer
from django.conf import settings

print("=" * 80)
print("ПОЛУЧЕНИЕ СПИСКА ACCESS LEVEL GROUPS")
print("=" * 80)

# Получаем HikCentral Server из БД
server = HikCentralServer.objects.filter(enabled=True).first()
if not server:
    print("❌ HikCentral Server не настроен в БД")
    sys.exit(1)

session = HikCentralSession(server)

print("✅ Сессия создана")

# Получаем Access Control Groups (type=1)
print("\n" + "=" * 80)
print("ACCESS CONTROL GROUPS (type=1)")
print("=" * 80)

response = session._make_request('POST', '/artemis/api/acs/v1/privilege/group', data={
    'pageNo': 1,
    'pageSize': 100,
    'type': 1
})

result = response.json()
if result.get('code') == '0':
    groups = result.get('data', {}).get('list', [])
    print(f"\nНайдено групп: {len(groups)}")
    
    for group in groups:
        print(f"\n  ID: {group.get('privilegeGroupId')}")
        print(f"  Name: {group.get('privilegeGroupName')}")
        print(f"  Description: {group.get('description', 'N/A')}")
        print(f"  Person Count: {group.get('personCount', 0)}")
else:
    print(f"❌ Ошибка: code={result.get('code')} msg={result.get('msg')}")

# Получаем Visitor Groups (type=2)
print("\n" + "=" * 80)
print("VISITOR ACCESS GROUPS (type=2)")
print("=" * 80)

response = session._make_request('POST', '/artemis/api/acs/v1/privilege/group', data={
    'pageNo': 1,
    'pageSize': 100,
    'type': 2
})

result = response.json()
if result.get('code') == '0':
    groups = result.get('data', {}).get('list', [])
    print(f"\nНайдено групп: {len(groups)}")
    
    for group in groups:
        print(f"\n  ID: {group.get('privilegeGroupId')}")
        print(f"  Name: {group.get('privilegeGroupName')}")
        print(f"  Description: {group.get('description', 'N/A')}")
        print(f"  Person Count: {group.get('personCount', 0)}")
        
        # Если это наша группа - выделяем
        if 'Visitors' in group.get('privilegeGroupName', ''):
            print("  ⭐ ЭТО НАША ГРУППА!")
else:
    print(f"❌ Ошибка: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("ГОТОВО")
print("=" * 80)
