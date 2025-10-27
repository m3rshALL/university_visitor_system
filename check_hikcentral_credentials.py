#!/usr/bin/env python
"""
Скрипт для проверки credentials HikCentral Professional
Проверяет наличие и корректность integration_key и integration_secret
"""
import os
import django
import sys

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'visitor_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.models import HikCentralServer

def check_credentials():
    """Проверяет credentials HikCentral в базе данных"""
    print("=" * 70)
    print("ПРОВЕРКА CREDENTIALS HIKCENTRAL PROFESSIONAL")
    print("=" * 70)
    
    servers = HikCentralServer.objects.all()
    
    if not servers.exists():
        print("\n[ERROR] В базе данных нет серверов HikCentral!")
        print("\nРешение:")
        print("1. Откройте Django Admin: http://localhost:8000/admin/")
        print("2. Перейдите в 'Hikvision Integration' -> 'Серверы HikCentral'")
        print("3. Добавьте сервер HikCentral Professional")
        return False
    
    enabled_servers = servers.filter(enabled=True)
    
    if not enabled_servers.exists():
        print("\n[WARNING] Нет активных серверов HikCentral!")
        print(f"   Всего серверов: {servers.count()}")
        print("\nРешение:")
        print("1. Откройте Django Admin")
        print("2. Активируйте один из серверов (поле 'Включен')")
        return False
    
    print(f"\n[OK] Найдено серверов: {servers.count()}")
    print(f"[OK] Активных серверов: {enabled_servers.count()}\n")
    
    all_ok = True
    
    for i, server in enumerate(servers, 1):
        print("-" * 70)
        print(f"Сервер #{i}: {server.name}")
        print("-" * 70)
        print(f"URL:              {server.base_url}")
        print(f"Включен:          {'[ДА]' if server.enabled else '[НЕТ]'}")
        print(f"Обновлен:         {server.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Проверка integration_key
        if not server.integration_key:
            print(f"\n[ERROR] КРИТИЧЕСКАЯ ОШИБКА: Integration Key пуст!")
            all_ok = False
        else:
            key_masked = server.integration_key[:8] + "..." + server.integration_key[-4:] if len(server.integration_key) > 12 else "***"
            print(f"\nIntegration Key:  {key_masked} (длина: {len(server.integration_key)} символов)")
            
            if len(server.integration_key) < 10:
                print(f"  [WARNING] Подозрительно короткий ключ!")
                all_ok = False
        
        # Проверка integration_secret
        if not server.integration_secret:
            print(f"[ERROR] КРИТИЧЕСКАЯ ОШИБКА: Integration Secret пуст!")
            all_ok = False
        else:
            secret_masked = "***" + server.integration_secret[-4:] if len(server.integration_secret) > 4 else "***"
            print(f"Integration Secret: {secret_masked} (длина: {len(server.integration_secret)} символов)")
            
            if len(server.integration_secret) < 20:
                print(f"  [WARNING] Подозрительно короткий секрет!")
                all_ok = False
        
        print()
    
    print("=" * 70)
    
    if all_ok:
        print("\n[SUCCESS] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\nЕсли код 64 все еще появляется:")
        print("1. Проверьте, что Integration Key/Secret совпадают с HikCentral")
        print("2. Откройте HikCentral -> System -> Security -> Integration Partner")
        print("3. Убедитесь, что Partner статус = Enabled")
        print("4. Убедитесь, что назначены правильные права доступа")
    else:
        print("\n[ERROR] ОБНАРУЖЕНЫ ОШИБКИ В CREDENTIALS!")
        print("\nКак исправить:")
        print("1. Откройте HikCentral Professional")
        print("2. Перейдите: System -> Security -> Integration Partner")
        print("3. Создайте или откройте Integration Partner")
        print("4. Скопируйте AppKey и AppSecret")
        print("5. Откройте Django Admin: http://localhost:8000/admin/")
        print("6. Обновите сервер HikCentral:")
        print("   - Integration Partner Key = AppKey")
        print("   - Integration Partner Secret = AppSecret")
        print("7. Перезапустите Celery worker")
    
    print("=" * 70)
    return all_ok


if __name__ == '__main__':
    try:
        success = check_credentials()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

