from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession


CANDIDATES = [
    '/artemis/api/common/v1/version',
    '/artemis/api/common/v1/version/detail',
    '/artemis/api/common/v1/server/info',
    '/artemis/api/common/v1/system/info',
    '/artemis/api/common/v1/system/capabilities',
]


class Command(BaseCommand):
    help = 'Пробует несколько common-эндпоинтов HikCentral и выводит ответы'

    def handle(self, *args, **options):
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            self.stdout.write(self.style.ERROR('Нет активных серверов HikCentral.'))
            return

        session = HikCentralSession(server)
        self.stdout.write(f"Проба эндпоинтов на {server.base_url}\n")

        for ep in CANDIDATES:
            self.stdout.write(self.style.WARNING(f"→ GET {ep}"))
            try:
                resp = session._make_request('GET', ep)
                text = resp.text
                self.stdout.write(self.style.SUCCESS(f"  HTTP {resp.status_code}"))
                self.stdout.write(f"  Content-Type: {resp.headers.get('Content-Type')}")
                # Выводим первые 300 символов тела
                preview = (text[:300] + '...') if len(text) > 300 else text
                self.stdout.write("  Body: " + preview)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Ошибка: {e}"))
            self.stdout.write("")
