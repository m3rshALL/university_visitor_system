from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import test_hikcentral_connection


class Command(BaseCommand):
    help = 'Создает конфигурацию для HikCentral Professional сервера'

    def handle(self, *args, **options):
        # Получаем настройки из переменных окружения или используем значения по умолчанию
        server_config = {
            'name': 'HikCentral Professional',
            'base_url': 'https://your-hikcentral-server.com',  # Замените на реальный URL
            'integration_key': '12281453',
            'integration_secret': 'wZFhg7ZkoYCTRF3JiwPi',
            'username': 'admin',
            'password': 'DctvCnjznm20!',
            'enabled': True
        }

        self.stdout.write("Создание сервера HikCentral Professional...")
        
        server, created = HikCentralServer.objects.get_or_create(
            name=server_config['name'],
            defaults=server_config
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Создан сервер: {server.name} ({server.base_url})")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠ Сервер уже существует: {server.name} ({server.base_url})")
            )

        # Тестируем подключение
        self.stdout.write("\n🔍 Тестирование подключения к HikCentral...")
        
        result = test_hikcentral_connection(server)
        
        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {server.name} - Подключение успешно\n"
                    f"  URL: {result['base_url']}\n"
                    f"  Версия: {result['version']}\n"
                    f"  Сборка: {result['build_time']}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ {server.name} - Ошибка подключения: {result['error']}"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Возможные причины:\n"
                    "1. Неправильный URL сервера HikCentral\n"
                    "2. Неправильные Integration Partner Key/Secret\n"
                    "3. Сервер недоступен или требует VPN\n"
                    "4. Неправильные учетные данные пользователя"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Настройка завершена!")
        )
        self.stdout.write("\n📋 Следующие шаги:")
        self.stdout.write("1. Обновите base_url в админке на реальный URL вашего HikCentral сервера")
        self.stdout.write("2. Проверьте Integration Partner Key/Secret")
        self.stdout.write("3. Убедитесь, что сервер HikCentral доступен из вашей сети")
        self.stdout.write("4. Протестируйте регистрацию гостя с FaceID")
