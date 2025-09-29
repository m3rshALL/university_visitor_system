#!/usr/bin/env python3
"""
Тест Basic Auth с HikCentral
"""
import requests
import urllib3
import json
import base64

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройки
base_url = 'https://10.1.18.29:444'
username = 'admin'
password = 'DctvCnjznm20!'

print("🔍 Тестирование Basic Auth с HikCentral")
print("=" * 60)

# Тест 1: Basic Auth для получения токена
print(f"\n🔑 Basic Auth для получения токена")
token_url = f"{base_url}/artemis-uaa/oauth/token"

# Создаем Basic Auth заголовок
credentials = f"{username}:{password}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/x-www-form-urlencoded'
}

data = {
    'grant_type': 'client_credentials',
    'scope': 'all'
}

try:
    response = requests.post(token_url, data=data, headers=headers, verify=False, timeout=10)
    print(f"📊 Статус ответа: {response.status_code}")
    print(f"📋 Заголовки ответа: {dict(response.headers)}")
    print(f"📄 Тело ответа: {response.text[:500]}...")
    
    if response.status_code == 200:
        try:
            token_data = response.json()
            print(f"✅ JSON ответ получен: {json.dumps(token_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"❌ Ответ не является валидным JSON")
    else:
        print(f"❌ Ошибка получения токена: {response.status_code}")
        
except Exception as e:
    print(f"❌ Ошибка запроса: {e}")

# Тест 2: Прямой API вызов с Basic Auth
print(f"\n🔍 Прямой API вызов с Basic Auth")
api_url = f"{base_url}/artemis/api/common/v1/version"

headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(api_url, headers=headers, verify=False, timeout=10)
    print(f"📊 Статус ответа: {response.status_code}")
    print(f"📄 Тело ответа: {response.text[:500]}...")
    
    if response.status_code == 200:
        print(f"✅ API доступен с Basic Auth!")
    else:
        print(f"❌ API недоступен: {response.status_code}")
        
except Exception as e:
    print(f"❌ Ошибка API запроса: {e}")

# Тест 3: Альтернативные endpoints для Basic Auth
print(f"\n🔍 Альтернативные endpoints для Basic Auth")
endpoints = [
    '/artemis/api/common/v1/version',
    '/api/common/v1/version',
    '/common/v1/version',
    '/artemis/api/system/version',
    '/api/system/version'
]

for endpoint in endpoints:
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        print(f"📡 {endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Рабочий API endpoint найден!")
            break
    except Exception as e:
        print(f"📡 {endpoint}: {e}")

print("\n" + "=" * 60)
print("✅ Тестирование завершено!")
