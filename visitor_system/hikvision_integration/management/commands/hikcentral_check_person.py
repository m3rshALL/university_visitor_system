from django.core.management.base import BaseCommand, CommandError
from typing import Optional
from hikvision_integration.models import HikPersonBinding
from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer


class Command(BaseCommand):
    help = "Проверка визитёра в HikCentral по Visitor API (visitorInfo, elementDownloadDetail, register records)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("guest_id", type=int, help="ID гостя в системе (используем как personCode)")
        parser.add_argument("--person-id", dest="person_id", type=str, default=None, help="personId в HCP (если уже известен)")
        parser.add_argument("--begin", dest="begin", type=str, default=None, help="Начало интервала (YYYY-MM-DDTHH:MM:SS)")
        parser.add_argument("--end", dest="end", type=str, default=None, help="Конец интервала (YYYY-MM-DDTHH:MM:SS)")

    def handle(self, *args, **options) -> None:
        guest_id: int = options["guest_id"]
        binding = HikPersonBinding.objects.filter(guest_id=guest_id).first()
        if not binding and not options.get("person_id"):
            raise CommandError("Binding не найден и person_id не указан. Сначала выполните enroll_face_task или передайте --person-id.")

        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            raise CommandError("HikCentralServer не настроен или выключен.")
        session = HikCentralSession(server)

        person_id = options.get("person_id") or binding.person_id
        person_code = str(guest_id)
        self.stdout.write(self.style.NOTICE(f"guest_id={guest_id} personCode={person_code} personId={person_id}"))

        # 1) Visitor info (по personId/personCode)
        try:
            payload = {
                'pageNo': 1,
                'pageSize': 10,
                'personId': str(person_id),
                'personCode': person_code,
            }
            resp = session._make_request('POST', '/artemis/api/visitor/v1/visitor/visitorInfo', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/visitor/v1/visitor/visitorInfo:")
            self.stdout.write(str(data))
            if isinstance(data, dict) and data.get('code') == '17':
                self.stdout.write(self.style.WARNING("No permission for OpenAPI access: проверьте права приложения на Visitor API"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/visitor/v1/visitor/visitorInfo error: {e}"))

        # 2) Элементы применения (детали) по personId
        try:
            uri = f"/artemis/api/visitor/v1/person/{person_id}/elementDownloadDetail"
            resp = session._make_request('POST', uri, data={})
            data = resp.json()
            self.stdout.write("/artemis/api/visitor/v1/person/{personId}/elementDownloadDetail:")
            self.stdout.write(str(data))
            if isinstance(data, dict) and data.get('code') == '8':
                self.stdout.write(self.style.WARNING("elementDownloadDetail: This product version is not supported — пропускаем"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/visitor/v1/person/{{personId}}/elementDownloadDetail error: {e}"))

        # 3) Записи регистрации визитёра
        try:
            from datetime import datetime, timedelta
            begin = options.get("begin")
            end = options.get("end")
            if not begin or not end:
                now = datetime.now()
                begin = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
                end = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
            payload = {
                'pageNo': 1,
                'pageSize': 10,
                'personId': str(person_id),
                # Для этого API требуются именно visitStartTime/visitEndTime
                'visitStartTime': begin,
                'visitEndTime': end,
            }
            resp = session._make_request('POST', '/artemis/api/visitor/v1/register/getVistorRegisterRecord', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/visitor/v1/register/getVistorRegisterRecord:")
            self.stdout.write(str(data))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/visitor/v1/register/getVistorRegisterRecord error: {e}"))

        self.stdout.write(self.style.SUCCESS("Проверка завершена (Visitor API)"))


