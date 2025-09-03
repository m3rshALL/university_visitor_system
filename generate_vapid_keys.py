#!/usr/bin/env python3
"""
Скрипт для генерации VAPID ключей для WebPush уведомлений
"""

try:
    from webpush import generate_vapid_keys
    
    # Генерируем VAPID ключи
    vapid_keys = generate_vapid_keys()
    
    print("=== VAPID ключи для WebPush уведомлений ===")
    print()
    print("Добавьте следующие переменные в ваш .env файл:")
    print()
    print(f"VAPID_PRIVATE_KEY={vapid_keys['private_key']}")
    print(f"VAPID_PUBLIC_KEY={vapid_keys['public_key']}")
    print("VAPID_ADMIN_EMAIL=maroccocombo@gmail.com")
    print()
    print("Не забудьте:")
    print("1. Заменить your-email@example.com на ваш реальный email")
    print("2. Добавить эти переменные в продакшн окружение")
    print("3. Перезапустить сервер после добавления ключей")
    print()
    print("ВАЖНО: Храните приватный ключ в безопасности!")
    
except ImportError:
    print("Ошибка: библиотека django-webpush не установлена")
    print("Установите её командой: pip install django-webpush")
except Exception as e:
    print(f"Ошибка генерации ключей: {e}")
