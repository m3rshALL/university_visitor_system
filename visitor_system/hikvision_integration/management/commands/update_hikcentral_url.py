from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer


class Command(BaseCommand):
    help = 'Обновляет URL сервера HikCentral на реальный'

    def handle(self, *args, **options):
        real_url = 'https://10.1.18.29:444'
        
        self.stdout.write("Обновление URL сервера HikCentral...")
        
        try:
            server = HikCentralServer.objects.get(name='HikCentral Professional')
            old_url = server.base_url
            server.base_url = real_url
            server.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ URL обновлен: {old_url} → {real_url}")
            )
            
        except HikCentralServer.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("❌ Сервер HikCentral Professional не найден")
            )
            self.stdout.write("Создайте сервер командой: python manage.py setup_hikcentral")

        self.stdout.write(self.style.SUCCESS("\n✓ Обновление завершено!"))
        self.stdout.write("\n📋 Следующий шаг:")
        self.stdout.write("Протестируйте подключение: python manage.py test_hikcentral_connection")
