#!/usr/bin/env python3
"""
Простой тест доступности устройств Hikvision
"""
import requests
import urllib3
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

devices = [
    {'host': '10.200.2.0', 'port': 8000, 'name': 'Паркинг вход'},
    {'host': '10.200.2.1', 'port': 8000, 'name': 'Паркинг выход'},
    {'host': '10.1.18.50', 'port': 8000, 'name': 'Турникет выход'},
    {'host': '10.1.18.47', 'port': 8000, 'name': 'Турникет вход'},
]

username = 'admin'
password = 'DctvCnjznm20!'

print("🔍 Тестирование доступности устройств Hikvision")
print("=" * 60)

for device in devices:
    host = device['host']
    port = device['port']
    name = device['name']
    
    print(f"\n📡 Тестирование {name} ({host}:{port})")
    
    # Тест 1: Базовая доступность HTTPS
    try:
        url = f"https://{host}:{port}"
        response = requests.get(url, verify=False, timeout=5)
        print(f"✅ HTTPS доступен: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTPS недоступен: {e}")
        continue
    
    # Тест 2: ISAPI endpoint с Digest Auth
    try:
        url = f"https://{host}:{port}/ISAPI/System/deviceInfo"
        auth = HTTPDigestAuth(username, password)
        response = requests.get(url, auth=auth, verify=False, timeout=10)
        print(f"✅ ISAPI Digest Auth: {response.status_code}")
        if response.status_code == 200:
            print(f"   Ответ: {response.text[:100]}...")
    except Exception as e:
        print(f"❌ ISAPI Digest Auth: {e}")
    
    # Тест 3: ISAPI endpoint с Basic Auth
    try:
        url = f"https://{host}:{port}/ISAPI/System/deviceInfo"
        auth = HTTPBasicAuth(username, password)
        response = requests.get(url, auth=auth, verify=False, timeout=10)
        print(f"✅ ISAPI Basic Auth: {response.status_code}")
        if response.status_code == 200:
            print(f"   Ответ: {response.text[:100]}...")
    except Exception as e:
        print(f"❌ ISAPI Basic Auth: {e}")
    
    # Тест 4: Альтернативный endpoint
    try:
        url = f"https://{host}:{port}/ISAPI/System/status"
        auth = HTTPDigestAuth(username, password)
        response = requests.get(url, auth=auth, verify=False, timeout=10)
        print(f"✅ ISAPI Status: {response.status_code}")
    except Exception as e:
        print(f"❌ ISAPI Status: {e}")

print("\n" + "=" * 60)
print("✅ Тестирование завершено!")
