from django.core.management.base import BaseCommand
from hikvision_integration.models import HikDevice
from hikvision_integration.services import test_device_connection


class Command(BaseCommand):
    help = 'Тестирует подключение ко всем устройствам Hikvision'

    def handle(self, *args, **options):
        devices = HikDevice.objects.filter(enabled=True)
        
        if not devices.exists():
            self.stdout.write(self.style.WARNING("Нет активных устройств Hikvision для тестирования."))
            return

        self.stdout.write("Тестирование подключения к устройствам Hikvision...\n")
        
        success_count = 0
        total_count = devices.count()
        
        for device in devices:
            self.stdout.write(f"Тестирование {device.host} ({device.name})...")
            
            result = test_device_connection(device)
            
            if result['status'] == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {device.host} - Подключение успешно\n"
                        f"  Модель: {result['model']}\n"
                        f"  Прошивка: {result['firmware']}\n"
                        f"  Серийный номер: {result['serial']}"
                    )
                )
                success_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ {device.host} - Ошибка подключения: {result['error']}"
                    )
                )
            
            self.stdout.write("")  # Пустая строка для разделения
        
        # Итоговая статистика
        self.stdout.write("=" * 50)
        self.stdout.write(f"Результаты тестирования: {success_count}/{total_count} устройств доступны")
        
        if success_count == total_count:
            self.stdout.write(self.style.SUCCESS("✓ Все устройства доступны!"))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠ Частично доступны: {total_count - success_count} устройств недоступны"))
        else:
            self.stdout.write(self.style.ERROR("✗ Ни одно устройство недоступно!"))
        
        self.stdout.write("\nСледующие шаги:")
        if success_count > 0:
            self.stdout.write("1. Запустите Celery worker для обработки задач")
            self.stdout.write("2. Настройте HIK_WEBHOOK_SECRET в переменных окружения")
            self.stdout.write("3. Протестируйте регистрацию гостя с FaceID")
        else:
            self.stdout.write("1. Проверьте сетевые настройки и доступность устройств")
            self.stdout.write("2. Убедитесь в правильности учетных данных")
            self.stdout.write("3. Проверьте настройки брандмауэра")
