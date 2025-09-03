#!/usr/bin/env python3
"""
Скрипт для генерации VAPID ключей для WebPush уведомлений
"""


import os
from py_vapid import Vapid
import base64

def generate_vapid_keys():
    """
    Генерирует VAPID ключи для WebPush уведомлений
    """
    print("🔑 Генерация VAPID ключей для WebPush...")
    
    try:
        # Создаем новый объект Vapid
        vapid = Vapid()
        
        # Генерируем ключи
        vapid.generate_keys()
        
        # Получаем ключи в правильном формате
        private_key_bytes = vapid.private_key.private_bytes(
            encoding=vapid.private_key.private_bytes.__defaults__[0],  # serialization.Encoding.PEM
            format=vapid.private_key.private_bytes.__defaults__[1],    # serialization.PrivateFormat.PKCS8
            encryption_algorithm=vapid.private_key.private_bytes.__defaults__[2]  # serialization.NoEncryption()
        )
        
        public_key_bytes = vapid.public_key.public_bytes(
            encoding=vapid.public_key.public_bytes.__defaults__[0],  # serialization.Encoding.PEM
            format=vapid.public_key.public_bytes.__defaults__[1]     # serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Конвертируем в base64url формат для WebPush
        private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
        public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
        
        print("✅ VAPID ключи успешно сгенерированы!")
        print("\n" + "="*60)
        print("📋 Скопируйте эти ключи в ваш .env файл:")
        print("="*60)
        print(f"VAPID_PRIVATE_KEY={private_key_b64}")
        print(f"VAPID_PUBLIC_KEY={public_key_b64}")
        print(f"VAPID_ADMIN_EMAIL=maroccocombo@gmail.com")
        print("="*60)
        
        # Автоматически обновляем .env файл
        env_path = os.path.join('visitor_system', 'visitor_system', 'conf', '.env')
        if os.path.exists(env_path):
            update_env_file(env_path, private_key_b64, public_key_b64)
        else:
            print(f"\n⚠️  Файл .env не найден по пути: {env_path}")
            print("Добавьте ключи в ваш .env файл вручную.")
        
        return private_key_b64, public_key_b64
        
    except Exception as e:
        print(f"❌ Ошибка при генерации ключей: {e}")
        print("\n🔧 Попробуйте альтернативный способ:")
        return generate_vapid_keys_alternative()

def generate_vapid_keys_alternative():
    """
    Альтернативный способ генерации с использованием более простого подхода
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
        import base64
        
        # Генерируем приватный ключ
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        
        # Сериализуем ключи
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Конвертируем в base64
        private_key_b64 = base64.urlsafe_b64encode(private_pem).decode('utf-8').rstrip('=')
        public_key_b64 = base64.urlsafe_b64encode(public_pem).decode('utf-8').rstrip('=')
        
        print("✅ VAPID ключи сгенерированы альтернативным способом!")
        print("\n" + "="*60)
        print("📋 Скопируйте эти ключи в ваш .env файл:")
        print("="*60)
        print(f"VAPID_PRIVATE_KEY={private_key_b64}")
        print(f"VAPID_PUBLIC_KEY={public_key_b64}")
        print(f"VAPID_ADMIN_EMAIL=maroccocombo@gmail.com")
        print("="*60)
        
        # Автоматически обновляем .env файл
        env_path = os.path.join('visitor_system', 'visitor_system', 'conf', '.env')
        if os.path.exists(env_path):
            update_env_file(env_path, private_key_b64, public_key_b64)
        
        return private_key_b64, public_key_b64
        
    except Exception as e:
        print(f"❌ Ошибка в альтернативном способе: {e}")
        return None, None

def update_env_file(env_path, private_key, public_key):
    """
    Обновляет .env файл с новыми VAPID ключами
    """
    try:
        # Читаем существующий файл
        with open(env_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Обновляем строки с ключами
        updated_lines = []
        private_updated = False
        public_updated = False
        
        for line in lines:
            if line.startswith('VAPID_PRIVATE_KEY='):
                updated_lines.append(f'VAPID_PRIVATE_KEY={private_key}\n')
                private_updated = True
            elif line.startswith('VAPID_PUBLIC_KEY='):
                updated_lines.append(f'VAPID_PUBLIC_KEY={public_key}\n')
                public_updated = True
            else:
                updated_lines.append(line)
        
        # Добавляем ключи, если их не было
        if not private_updated:
            updated_lines.append(f'VAPID_PRIVATE_KEY={private_key}\n')
        if not public_updated:
            updated_lines.append(f'VAPID_PUBLIC_KEY={public_key}\n')
        
        # Записываем обновленный файл
        with open(env_path, 'w', encoding='utf-8') as file:
            file.writelines(updated_lines)
        
        print(f"\n✅ Файл .env успешно обновлен: {env_path}")
        
    except Exception as e:
        print(f"\n⚠️  Ошибка при обновлении .env файла: {e}")
        print("Добавьте ключи в .env файл вручную.")

if __name__ == "__main__":
    generate_vapid_keys()
