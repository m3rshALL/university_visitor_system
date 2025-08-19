#!/usr/bin/env python
"""
Скрипт для быстрого добавления API ключа egov.kz
Использование: python setup_api_key.py
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

from egov_integration.models import EgovSettings
from django.contrib.auth.models import User


def setup_api_key():
    """Настройка API ключа"""
    
    # API ключ из файла example.env
    api_key = "63092dca612f4a79b9c019c06ea21b3a"
    
    print("🔑 Настройка API ключа egov.kz...")
    
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        
        # Обновляем API ключ
        setting, created = EgovSettings.objects.update_or_create(
            name='EGOV_API_KEY',
            defaults={
                'value': api_key,
                'is_encrypted': False,  # Пока не шифруем для тестирования
                'description': 'API ключ для egov.kz',
                'updated_by': admin_user
            }
        )
        
        status = "создан" if created else "обновлен"
        print(f"   ✓ EGOV_API_KEY: {status}")
        
        # Обновляем базовый URL
        setting, created = EgovSettings.objects.update_or_create(
            name='EGOV_BASE_URL',
            defaults={
                'value': 'https://data.egov.kz/api/v4',
                'is_encrypted': False,
                'description': 'Базовый URL API egov.kz',
                'updated_by': admin_user
            }
        )
        
        status = "создан" if created else "обновлен"
        print(f"   ✓ EGOV_BASE_URL: {status}")
        
        print("\n✅ API ключ успешно настроен!")
        print(f"   API Key: {api_key}")
        print(f"   Base URL: https://data.egov.kz/api/v4")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False


def test_settings():
    """Тест настроек"""
    print("\n🔧 Проверка настроек...")
    
    try:
        from egov_integration.services import egov_service
        
        # Сбрасываем кеш настроек
        egov_service._settings_loaded = False
        
        print(f"   Base URL: {egov_service.base_url}")
        print(f"   API Key: {egov_service.api_key[:10]}..." if egov_service.api_key else "   API Key: ✗ Не настроен")
        print(f"   Timeout: {egov_service.timeout}s")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False


def main():
    print("🚀 Быстрая настройка API ключа egov.kz")
    print("=" * 50)
    
    if setup_api_key():
        test_settings()
        print("\n📝 Следующие шаги:")
        print("1. Запустите тест: python egov_integration/test_api.py")
        print("2. Проверьте интеграцию в формах регистрации")
        print("3. Мониторьте логи в админ панели")
    else:
        print("\n❌ Настройка не удалась")


if __name__ == '__main__':
    main()
