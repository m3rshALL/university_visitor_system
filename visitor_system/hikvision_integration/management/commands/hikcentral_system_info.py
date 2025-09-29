from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession


class Command(BaseCommand):
    help = 'Запрашивает /artemis/api/common/v1/system/info и выводит ответ'

    def handle(self, *args, **options):
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            self.stdout.write(self.style.ERROR('Нет активных серверов HikCentral.'))
            return

        self.stdout.write(f"Запрос system info у: {server.base_url}\n")
        try:
            session = HikCentralSession(server)
            resp = session._make_request('GET', '/artemis/api/common/v1/system/info')
            self.stdout.write(self.style.SUCCESS(f"HTTP {resp.status_code}"))
            self.stdout.write("\nЗаголовки:")
            for k, v in resp.headers.items():
                self.stdout.write(f"{k}: {v}")
            self.stdout.write("\nТело ответа:")
            self.stdout.write(resp.text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
