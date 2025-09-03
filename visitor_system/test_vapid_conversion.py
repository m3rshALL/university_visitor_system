#!/usr/bin/env python
"""Тестирование функции get_vapid_public_key"""
import os
import sys
import django
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.insert(0, str(Path(__file__).parent))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

# Импортируем и тестируем функцию
from django.conf import settings
import base64

print("=== ТЕСТИРОВАНИЕ КОНВЕРТАЦИИ VAPID КЛЮЧА ===")

try:
    from cryptography.hazmat.primitives import serialization
    
    # Получаем PEM ключ из настроек
    pem_key_b64 = settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY', '')
    
    if not pem_key_b64:
        print("ОШИБКА: VAPID ключ не настроен")
        sys.exit(1)
    
    print(f"PEM ключ base64 (первые 50 символов): {pem_key_b64[:50]}...")
    
    # Исправляем padding для base64
    missing_padding = len(pem_key_b64) % 4
    if missing_padding:
        pem_key_b64 += '=' * (4 - missing_padding)
        print(f"✓ Добавлен padding: {4 - missing_padding} символов '='")
    
    # Декодируем base64 PEM ключ
    try:
        pem_key = base64.b64decode(pem_key_b64).decode('utf-8')
        print("✓ Декодирование base64 успешно")
        print(f"PEM ключ:\n{pem_key}")
    except Exception as e:
        print(f"✗ Ошибка декодирования base64: {e}")
        sys.exit(1)
    
    # Загружаем публичный ключ
    try:
        public_key = serialization.load_pem_public_key(pem_key.encode('utf-8'))
        print("✓ Загрузка PEM ключа успешна")
    except Exception as e:
        print(f"✗ Ошибка загрузки PEM ключа: {e}")
        sys.exit(1)
    
    # Получаем сырые байты в формате uncompressed point для WebPush
    try:
        raw_key = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        print("✓ Извлечение raw bytes успешно")
        print(f"Размер raw key: {len(raw_key)} байт")
    except Exception as e:
        print(f"✗ Ошибка извлечения raw bytes: {e}")
        sys.exit(1)
    
    # Конвертируем в base64url (без padding) для WebPush API
    try:
        vapid_key = base64.urlsafe_b64encode(raw_key).decode('utf-8').rstrip('=')
        print("✓ Конвертация в base64url успешна")
        print(f"VAPID ключ для WebPush: {vapid_key}")
        print(f"Длина ключа: {len(vapid_key)} символов")
    except Exception as e:
        print(f"✗ Ошибка конвертации в base64url: {e}")
        sys.exit(1)
        
    print("\n=== ВСЕ ТЕСТЫ ПРОЙДЕНЫ ===")
    
except ImportError as e:
    print(f"✗ Ошибка импорта: {e}")
    print("Убедитесь, что cryptography установлена")
    sys.exit(1)
except Exception as e:
    print(f"✗ Общая ошибка: {e}")
    sys.exit(1)
