#!/usr/bin/env python3
"""
Тест доступности устройств Hikvision с разными портами и протоколами
"""
import requests
import urllib3
from requests.auth import HTTPDigestAuth

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

devices = [
    {'host': '10.200.2.0', 'name': 'Паркинг вход'},
    {'host': '10.200.2.1', 'name': 'Паркинг выход'},
    {'host': '10.1.18.50', 'name': 'Турникет выход'},
    {'host': '10.1.18.47', 'name': 'Турникет вход'},
]

ports = [80, 443, 8000, 8080, 8443]
protocols = ['http', 'https']

username = 'admin'
password = 'DctvCnjznm20!'

print("🔍 Тестирование доступности с разными портами и протоколами")
print("=" * 70)

for device in devices:
    host = device['host']
    name = device['name']
    
    print(f"\n📡 Тестирование {name} ({host})")
    print("-" * 50)
    
    found_working = False
    
    for protocol in protocols:
        for port in ports:
            try:
                url = f"{protocol}://{host}:{port}"
                response = requests.get(url, verify=False, timeout=3)
                print(f"✅ {protocol.upper()} {port}: {response.status_code}")
                found_working = True
                
                # Если HTTP работает, пробуем ISAPI
                if protocol == 'http' and response.status_code in [200, 401, 403]:
                    try:
                        isapi_url = f"{url}/ISAPI/System/deviceInfo"
                        auth = HTTPDigestAuth(username, password)
                        isapi_response = requests.get(isapi_url, auth=auth, verify=False, timeout=5)
                        print(f"   📋 ISAPI: {isapi_response.status_code}")
                        if isapi_response.status_code == 200:
                            print(f"   🎉 Устройство найдено! Используйте: {protocol}://{host}:{port}")
                    except Exception as e:
                        print(f"   ❌ ISAPI: {e}")
                        
            except requests.exceptions.ConnectTimeout:
                pass  # Таймаут - порт не отвечает
            except requests.exceptions.ConnectionError as e:
                if "Connection refused" in str(e):
                    pass  # Порт закрыт
                else:
                    print(f"❌ {protocol.upper()} {port}: {e}")
            except Exception as e:
                print(f"❌ {protocol.upper()} {port}: {e}")
    
    if not found_working:
        print("❌ Устройство недоступно на всех тестируемых портах")

print("\n" + "=" * 70)
print("✅ Тестирование завершено!")
print("\n💡 Если найдены рабочие устройства, обновите конфигурацию в админке.")
