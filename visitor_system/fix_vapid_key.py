#!/usr/bin/env python
"""
Скрипт для извлечения правильного формата VAPID ключа для WebPush API
"""
import base64
import os
import sys

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')

try:
    from cryptography.hazmat.primitives import serialization
    
    # Декодируем base64 PEM ключ из .env
    pem_key_b64 = 'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFbFZpdDM3MDZYZ0VKRTZ3WEFCNEtONzNiQU91bgp0YUViK1h4ZnAvS0pqWEZVVkNpMkoxMm5hUUwydGpJa09GNm9PL1Uyd2NnYjgzSzVVVHM3c1FTTEJ3PT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg'
    
    print("=== VAPID Ключ Конвертер ===")
    
    # Декодируем PEM ключ
    pem_key = base64.b64decode(pem_key_b64).decode('utf-8')
    print("PEM ключ:")
    print(pem_key)
    print()
    
    # Загружаем публичный ключ
    public_key = serialization.load_pem_public_key(pem_key.encode('utf-8'))
    
    # Получаем сырые байты в формате uncompressed point
    raw_key = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Конвертируем в base64url для WebPush
    vapid_key = base64.urlsafe_b64encode(raw_key).decode('utf-8').rstrip('=')
    
    print("VAPID ключ для WebPush API:")
    print(vapid_key)
    print()
    print("Длина ключа:", len(vapid_key))
    print("Первые 10 символов:", vapid_key[:10])
    
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что установлены все зависимости")
    sys.exit(1)
except Exception as e:
    print(f"Ошибка: {e}")
    sys.exit(1)
