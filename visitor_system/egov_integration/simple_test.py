#!/usr/bin/env python
"""
Простой тест подключения к egov.kz
"""

import requests
import json

def test_egov_connection():
    """Простой тест подключения к egov.kz"""
    
    api_key = "b1f82af3b06e4db1a0841d03146cf2ea"
    base_url = "https://data.egov.kz/api/v4"
    
    print("🧪 Простой тест подключения к egov.kz")
    print("=" * 50)
    
    # Тест 1: Проверка доступности портала
    print("1️⃣ Проверка доступности портала...")
    try:
        response = requests.get("https://data.egov.kz", timeout=10)
        print(f"   Статус: {response.status_code}")
        print(f"   ✓ Портал доступен" if response.status_code == 200 else f"   ✗ Проблема с порталом")
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
    
    # Тест 2: Проверка API с ключом
    print("\n2️⃣ Проверка API с ключом...")
    try:
        url = f"{base_url}/health?apiKey={api_key}"
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ API доступен")
            try:
                data = response.json()
                print(f"   Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   Ответ (text): {response.text[:200]}...")
        else:
            print(f"   ✗ Ошибка API: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
    
    # Тест 3: Получение списка datasets
    print("\n3️⃣ Получение списка наборов данных...")
    try:
        url = f"{base_url}/datasets?apiKey={api_key}"
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"   ✓ Найдено {len(data)} наборов данных")
                    # Показываем первые 3
                    for i, dataset in enumerate(data[:3]):
                        if isinstance(dataset, dict):
                            name = dataset.get('name', dataset.get('title', 'Неизвестно'))
                            print(f"   - {name}")
                else:
                    print(f"   Ответ: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
            except:
                print(f"   Ответ (text): {response.text[:300]}...")
        else:
            print(f"   ✗ Ошибка: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("📝 Рекомендации:")
    print("1. Если портал недоступен - проверьте интернет соединение")
    print("2. Если API не работает - проверьте корректность API ключа")
    print("3. Изучите документацию: https://data.egov.kz/pages/samples")


if __name__ == '__main__':
    test_egov_connection()
