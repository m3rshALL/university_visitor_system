import json
from django.core.management.base import BaseCommand
from hikvision_integration.models import HikDevice, HikFaceLibrary


class Command(BaseCommand):
    help = 'Создает конфигурацию для всех 4 устройств Hikvision'

    def handle(self, *args, **options):
        devices_config = [
        {
            'name': 'Паркинг вход',
            'host': '10.200.2.0',
            'port': 8000,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250121V043900ENFX3906159',
            'firmware': 'V4.39.0 build 250121',
            'is_primary': True,
            'doors_json': ['door1'],  # Паркинг вход
            'description': 'Устройство контроля входа на паркинг'
        },
        {
            'name': 'Паркинг выход',
            'host': '10.200.2.1',
            'port': 8000,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250121V043900ENFX3906188',
            'firmware': 'V4.39.0 build 250121',
            'is_primary': False,
            'doors_json': ['door2'],  # Паркинг выход
            'description': 'Устройство контроля выхода с паркинга'
        },
        {
            'name': 'Турникет выход',
            'host': '10.1.18.50',
            'port': 8000,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250703V044101ENAK0468614',
            'firmware': 'V4.41.1 build 250703',
            'is_primary': False,
            'doors_json': ['door3'],  # Турникет выход
            'description': 'Турникет для выхода из здания'
        },
        {
            'name': 'Турникет вход',
            'host': '10.1.18.47',
            'port': 8000,
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'model': 'DS-K1T673DWX20250703V044101ENAK0477599',
            'firmware': 'V4.41.1 build 250703',
            'is_primary': False,
            'doors_json': ['door4'],  # Турникет вход
            'description': 'Турникет для входа в здание'
        }
        ]

        self.stdout.write("Создание устройств Hikvision...")
        
        for config in devices_config:
            device, created = HikDevice.objects.get_or_create(
                host=config['host'],
                defaults={
                    'name': config['name'],
                    'port': config['port'],
                    'username': config['username'],
                    'password': config['password'],
                    'verify_ssl': False,  # Для самоподписанных сертификатов
                    'is_primary': config['is_primary'],
                    'enabled': True,
                    'doors_json': config['doors_json']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Создано устройство: {config['name']} ({config['host']})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Устройство уже существует: {config['name']} ({config['host']})")
                )

        # Создаем библиотеки лиц для каждого устройства
        self.stdout.write("\nСоздание библиотек лиц...")
        
        for device in HikDevice.objects.filter(enabled=True):
            face_lib, created = HikFaceLibrary.objects.get_or_create(
                device=device,
                library_id='1',  # Стандартная библиотека лиц
                defaults={
                    'name': f'Основная библиотека лиц - {device.host}'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Создана библиотека лиц для {device.host}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Библиотека лиц уже существует для {device.host}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Настройка завершена! Создано {len(devices_config)} устройств.")
        )
        self.stdout.write("\nСледующие шаги:")
        self.stdout.write("1. Проверьте устройства в админке: /admin/hikvision_integration/hikdevice/")
        self.stdout.write("2. Настройте HIK_WEBHOOK_SECRET в переменных окружения")
        self.stdout.write("3. Запустите Celery worker для обработки задач")
        self.stdout.write("4. Протестируйте webhook: /hikvision/webhook/")
