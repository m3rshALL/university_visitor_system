"""
Скрипт для тестирования API egov.kz
Использование: python test_api.py
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev')
django.setup()

from egov_integration.services import egov_service, EgovAPIException
from egov_integration.models import EgovSettings
from django.contrib.auth.models import User


def test_settings():
    """Тест настроек"""
    print("🔧 Проверка настроек...")
    
    try:
        print("Base URL: {}".format(egov_service.base_url))
        print(
            "API Key: {}".format(
                "✓ Настроен" if egov_service.api_key else "✗ Не настроен"
            )
        )
        print("Timeout: {}s".format(egov_service.timeout))
        print("Max Retries: {}".format(egov_service.max_retries))
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_api_health():
    """Тест доступности API"""
    print("\n🌐 Проверка доступности API...")
    
    try:
        health = egov_service.check_api_health()
        print(f"Статус: {health['status']}")
        
        if health['status'] == 'healthy':
            print("✓ API доступен")
            return True
        else:
            print(
                "✗ API недоступен: {}".format(
                    health.get('error', 'Неизвестная ошибка')
                )
            )
            return False
            
    except Exception as e:
        print("✗ Ошибка подключения: {}".format(e))
        return False


def test_iin_verification():
    """Тест проверки ИИН"""
    print("\n📋 Тест проверки ИИН...")
    
    # Используем тестовый ИИН (не реальный)
    test_iin = "123456789012"
    
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        result = egov_service.verify_iin(test_iin, user=admin_user)
        
        print(f"ИИН: {test_iin}")
        print(f"Статус: {result.status}")
        print(f"ID проверки: {result.id}")
        
        if result.error_message:
            print(f"Ошибка: {result.error_message}")
        
        if result.verified_data:
            print(f"Данные: {result.verified_data}")
        
        return result.status != 'failed'
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_database_settings():
    """Тест настроек в базе данных"""
    print("\n🗄️Проверка настроек в БД...")
    
    try:
        settings_count = EgovSettings.objects.count()
        print(f"Настроек в БД: {settings_count}")
        
        if settings_count > 0:
            for setting in EgovSettings.objects.all()[:5]:
                value_preview = "***" if setting.is_encrypted else setting.value[:50]
                print(f"-{setting.name}: {value_preview}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Ошибка БД: {e}")
        return False


def setup_test_settings():
    """Настройка тестовых параметров"""
    print("\n⚙️Настройка тестовых параметров...")
    
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        
        test_settings = [
            ('EGOV_BASE_URL', 'https://data.egov.kz/api/v4', False),
            ('EGOV_TIMEOUT', '30', False),
            ('EGOV_MAX_RETRIES', '3', False),
        ]
        
        for name, value, encrypted in test_settings:
            created = EgovSettings.objects.update_or_create(
                name=name,
                defaults={
                    'value': value,
                    'is_encrypted': encrypted,
                    'description': f'Тестовая настройка {name}',
                    'updated_by': admin_user
                }
            )
            status = "создана" if created else "обновлена"
            print(f"✓ {name}: {status}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Ошибка настройки: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование интеграции с egov.kz")
    print("=" * 50)
    
    tests = [
        ("Настройки", test_settings),
        ("База данных", test_database_settings),
        ("Настройка тестовых параметров", setup_test_settings),
        ("API Health", test_api_health),
        ("Проверка ИИН", test_iin_verification),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))
    
    # Итоги
    print("\n" + "=" * 50)
    print("📊 Результаты тестирования:")
    
    passed = 0
    for test_name, success in results:
        status = "✓ ПРОЙДЕН" if success else "✗ ОШИБКА"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(results)} тестов")
    
    if passed == len(results):
        print("🎉Все тесты пройдены успешно!")
    elif passed > len(results) // 2:
        print("⚠️Большинство тестов пройдено, но есть проблемы")
    else:
        print("🚨Критические проблемы с интеграцией")
    
    # Рекомендации
    print("\n📝 Следующие шаги:")
    print("1. Получите реальный API ключ на https://data.egov.kz/")
    print("2. Добавьте его в настройки через Django Admin")
    print("3. Протестируйте проверку реальных документов")
    print("4. Настройте мониторинг и логирование")


if __name__ == '__main__':
    main()
