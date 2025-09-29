#!/usr/bin/env python3
"""
Тест получения токена от HikCentral
"""
import requests
import urllib3
import json

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройки
base_url = 'https://10.1.18.29:444'
integration_key = '12281453'
integration_secret = 'wZFhg7ZkoYCTRF3JiwPi'

print("🔍 Тестирование получения токена от HikCentral")
print("=" * 60)

# Тест 1: Проверяем доступность сервера
print(f"\n📡 Тестирование доступности {base_url}")
try:
    response = requests.get(base_url, verify=False, timeout=10)
    print(f"✅ Сервер доступен: {response.status_code}")
    print(f"   Заголовки: {dict(response.headers)}")
except Exception as e:
    print(f"❌ Сервер недоступен: {e}")
    exit(1)

# Тест 2: Пробуем получить токен
print(f"\n🔑 Получение OAuth2 токена")
token_url = f"{base_url}/artemis-uaa/oauth/token"

data = {
    'grant_type': 'client_credentials',
    'client_id': integration_key,
    'client_secret': integration_secret,
    'scope': 'all'
}

try:
    response = requests.post(token_url, data=data, verify=False, timeout=10)
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

# Тест 3: Альтернативные endpoints
print(f"\n🔍 Тестирование альтернативных endpoints")
endpoints = [
    '/artemis-uaa/oauth/token',
    '/uaa/oauth/token',
    '/oauth/token',
    '/api/oauth/token',
    '/artemis/api/oauth/token'
]

for endpoint in endpoints:
    try:
        url = f"{base_url}{endpoint}"
        response = requests.post(url, data=data, verify=False, timeout=5)
        print(f"📡 {endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Рабочий endpoint найден!")
            break
    except Exception as e:
        print(f"📡 {endpoint}: {e}")

print("\n" + "=" * 60)
print("✅ Тестирование завершено!")
