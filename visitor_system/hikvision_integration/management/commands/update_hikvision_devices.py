from django.core.management.base import BaseCommand
from hikvision_integration.models import HikDevice


class Command(BaseCommand):
    help = 'Обновляет настройки существующих устройств Hikvision'

    def handle(self, *args, **options):
        devices_config = [
            {
                'host': '10.200.2.0',
                'port': 80,  # HTTP работает
                'verify_ssl': False,
            },
            {
                'host': '10.200.2.1',
                'port': 80,  # HTTP работает
                'verify_ssl': False,
            },
            {
                'host': '10.1.18.50',
                'port': 80,  # Попробуем HTTP
                'verify_ssl': False,
                'enabled': False,  # Отключаем недоступное устройство
            },
            {
                'host': '10.1.18.47',
                'port': 80,  # HTTP работает
                'verify_ssl': False,
            }
        ]

        self.stdout.write("Обновление настроек устройств Hikvision...")
        
        for config in devices_config:
            try:
                device = HikDevice.objects.get(host=config['host'])
                device.port = config['port']
                device.verify_ssl = config['verify_ssl']
                if 'enabled' in config:
                    device.enabled = config['enabled']
                device.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Обновлено устройство: {device.name} ({device.host}:{device.port})")
                )
            except HikDevice.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Устройство не найдено: {config['host']}")
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Обновление завершено!"))
