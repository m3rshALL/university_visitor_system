from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import test_hikcentral_connection


class Command(BaseCommand):
    help = 'Тестирует подключение к серверам HikCentral Professional'

    def handle(self, *args, **options):
        servers = HikCentralServer.objects.filter(enabled=True)
        
        if not servers.exists():
            self.stdout.write(self.style.WARNING("Нет активных серверов HikCentral для тестирования."))
            self.stdout.write("\n💡 Создайте сервер HikCentral командой: python manage.py setup_hikcentral")
            return

        self.stdout.write("Тестирование подключения к серверам HikCentral Professional...\n")
        
        success_count = 0
        total_count = servers.count()
        
        for server in servers:
            self.stdout.write(f"Тестирование {server.name} ({server.base_url})...")
            
            result = test_hikcentral_connection(server)
            
            if result['status'] == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {server.name} - Подключение успешно\n"
                        f"  URL: {result['base_url']}\n"
                        f"  Версия: {result['version']}\n"
                        f"  Сборка: {result['build_time']}"
                    )
                )
                success_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ {server.name} - Ошибка подключения: {result['error']}"
                    )
                )
            
            self.stdout.write("")  # Пустая строка для разделения
        
        # Итоговая статистика
        self.stdout.write("=" * 50)
        self.stdout.write(f"Результаты тестирования: {success_count}/{total_count} серверов доступны")
        
        if success_count == total_count:
            self.stdout.write(self.style.SUCCESS("✓ Все серверы HikCentral доступны!"))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠ Частично доступны: {total_count - success_count} серверов недоступны"))
        else:
            self.stdout.write(self.style.ERROR("✗ Ни один сервер HikCentral недоступен!"))
        
        self.stdout.write("\nСледующие шаги:")
        if success_count > 0:
            self.stdout.write("1. Запустите Celery worker для обработки задач")
            self.stdout.write("2. Настройте HIK_WEBHOOK_SECRET в переменных окружения")
            self.stdout.write("3. Протестируйте регистрацию гостя с FaceID")
        else:
            self.stdout.write("1. Проверьте URL сервера HikCentral в админке")
            self.stdout.write("2. Убедитесь в правильности Integration Partner Key/Secret")
            self.stdout.write("3. Проверьте доступность сервера HikCentral из вашей сети")
            self.stdout.write("4. Убедитесь, что сервер HikCentral запущен и работает")
