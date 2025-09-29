#!/usr/bin/env python3
"""
Скрипт для настройки Hikvision интеграции
"""
import os
import sys
import django
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent / 'visitor_system'
sys.path.insert(0, str(project_root))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.local')
django.setup()

from hikvision_integration.models import HikDevice
from hikvision_integration.services import test_device_connection


def setup_devices():
    """Настраивает устройства Hikvision"""
    print("🔧 Настройка устройств Hikvision...")
    
    devices_config = [
        {
            'name': 'Паркинг вход',
            'host': '10.200.2.0',
            'port': 80,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250121V043900ENFX3906159',
            'firmware': 'V4.39.0 build 250121',
            'is_primary': True,
            'doors_json': ['door1'],
            'description': 'Устройство контроля входа на паркинг'
        },
        {
            'name': 'Паркинг выход',
            'host': '10.200.2.1',
            'port': 80,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250121V043900ENFX3906188',
            'firmware': 'V4.39.0 build 250121',
            'is_primary': False,
            'doors_json': ['door2'],
            'description': 'Устройство контроля выхода с паркинга'
        },
        {
            'name': 'Турникет выход',
            'host': '10.1.18.50',
            'port': 80,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250703V044101ENAK0468614',
            'firmware': 'V4.41.1 build 250703',
            'is_primary': False,
            'doors_json': ['door3'],
            'description': 'Турникет для выхода из здания'
        },
        {
            'name': 'Турникет вход',
            'host': '10.1.18.47',
            'port': 80,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250703V044101ENAK0477599',
            'firmware': 'V4.41.1 build 250703',
            'is_primary': False,
            'doors_json': ['door4'],
            'description': 'Турникет для входа в здание'
        }
    ]

    for config in devices_config:
        device, created = HikDevice.objects.get_or_create(
            host=config['host'],
            defaults={
                'port': config['port'],
                'username': config['username'],
                'password': config['password'],
                'verify_ssl': False,
                'is_primary': config['is_primary'],
                'enabled': True,
                'doors_json': config['doors_json'],
                'description': config['description']
            }
        )
        
        if created:
            print(f"✅ Создано устройство: {config['name']} ({config['host']})")
        else:
            print(f"⚠️  Устройство уже существует: {config['name']} ({config['host']})")


def test_connections():
    """Тестирует подключения к устройствам"""
    print("\n🔍 Тестирование подключений...")
    
    devices = HikDevice.objects.filter(enabled=True)
    
    if not devices.exists():
        print("❌ Нет активных устройств для тестирования")
        return

    success_count = 0
    total_count = devices.count()
    
    for device in devices:
        print(f"\n📡 Тестирование {device.host}...")
        
        result = test_device_connection(device)
        
        if result['status'] == 'success':
            print(f"✅ {device.host} - Подключение успешно")
            print(f"   Модель: {result['model']}")
            print(f"   Прошивка: {result['firmware']}")
            print(f"   Серийный номер: {result['serial']}")
            success_count += 1
        else:
            print(f"❌ {device.host} - Ошибка: {result['error']}")
    
    print(f"\n📊 Результаты: {success_count}/{total_count} устройств доступны")
    
    if success_count == total_count:
        print("🎉 Все устройства доступны!")
    elif success_count > 0:
        print(f"⚠️  Частично доступны: {total_count - success_count} недоступны")
    else:
        print("❌ Ни одно устройство недоступно!")


def main():
    """Основная функция"""
    print("🚀 Настройка Hikvision интеграции")
    print("=" * 50)
    
    try:
        setup_devices()
        test_connections()
        
        print("\n" + "=" * 50)
        print("✅ Настройка завершена!")
        print("\n📋 Следующие шаги:")
        print("1. Установите HIK_WEBHOOK_SECRET в переменных окружения")
        print("2. Запустите Celery worker: celery -A visitor_system worker -l info")
        print("3. Протестируйте webhook: /hikvision/webhook/")
        print("4. Зарегистрируйте гостя для тестирования FaceID")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
