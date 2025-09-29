from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession


class Command(BaseCommand):
    help = 'POST /artemis/api/resource/v1/videoManagementServer (pageNo/pageSize) и вывод ответа'

    def handle(self, *args, **options):
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            self.stdout.write(self.style.ERROR('Нет активных серверов HikCentral.'))
            return

        session = HikCentralSession(server)
        endpoint = '/artemis/api/resource/v1/videoManagementServer'
        payload = {"pageNo": 1, "pageSize": 20}
        self.stdout.write(f"POST {endpoint} на {server.base_url} с {payload}\n")
        try:
            resp = session._make_request('POST', endpoint, data=payload)
            self.stdout.write(self.style.SUCCESS(f"HTTP {resp.status_code}"))
            self.stdout.write("\nЗаголовки:")
            for k, v in resp.headers.items():
                self.stdout.write(f"{k}: {v}")
            self.stdout.write("\nТело ответа:")
            self.stdout.write(resp.text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
