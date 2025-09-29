from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer


class Command(BaseCommand):
    help = 'Обновляет Integration Partner учетные данные для HikCentral'

    def handle(self, *args, **options):
        new_credentials = {
            'integration_key': '12281453',
            'integration_secret': 'wZFhg7ZkoYCTRF3JiwPi'
        }
        
        self.stdout.write("Обновление Integration Partner учетных данных...")
        
        try:
            server = HikCentralServer.objects.get(name='HikCentral Professional')
            
            old_key = server.integration_key
            old_secret = server.integration_secret
            
            server.integration_key = new_credentials['integration_key']
            server.integration_secret = new_credentials['integration_secret']
            # Очищаем старый токен, чтобы получить новый
            server.access_token = None
            server.token_expires_at = None
            server.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ Integration Key обновлен: {old_key} → {new_credentials['integration_key']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"✓ Integration Secret обновлен: {old_secret[:8]}... → {new_credentials['integration_secret'][:8]}...")
            )
            self.stdout.write(
                self.style.SUCCESS("✓ Старый токен очищен - будет получен новый")
            )
            
        except HikCentralServer.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("❌ Сервер HikCentral Professional не найден")
            )
            self.stdout.write("Создайте сервер командой: python manage.py setup_hikcentral")

        self.stdout.write(self.style.SUCCESS("\n✓ Обновление завершено!"))
        self.stdout.write("\n📋 Следующий шаг:")
        self.stdout.write("Протестируйте подключение: python manage.py test_hikcentral_connection")
