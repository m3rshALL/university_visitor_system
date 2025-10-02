from django.core.management.base import BaseCommand, CommandError
from typing import Optional
from hikvision_integration.models import HikPersonBinding
from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer


class Command(BaseCommand):
    help = "Проверка визитёра в HikCentral через Resource API и ACS API (без Visitor API)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("guest_id", type=int, help="ID гостя в системе (используем как personCode)")
        parser.add_argument("--person-id", dest="person_id", type=str, default=None, help="personId в HCP (если уже известен)")

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

        # 1) Проверка через Resource API - поиск по personCode
        try:
            payload = {
                'pageNo': 1, 
                'pageSize': 10,
                'personCode': person_code
            }
            resp = session._make_request('POST', '/artemis/api/resource/v1/person/advance/personList', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/resource/v1/person/advance/personList:")
            self.stdout.write(str(data))
            
            # Проверяем, есть ли результаты
            if data.get('code') == '0' and data.get('data', {}).get('total', 0) > 0:
                self.stdout.write(self.style.SUCCESS(f"Найдено персон: {data.get('data', {}).get('total', 0)}"))
                persons = data.get('data', {}).get('list', [])
                for p in persons:
                    self.stdout.write(f"Person ID: {p.get('personId')}, Имя: {p.get('personName')}, Код: {p.get('personCode')}")
            else:
                self.stdout.write(self.style.WARNING("Персона не найдена по коду"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/resource/v1/person/advance/personList error: {e}"))

        # 2) Проверка информации о персоне по personId
        try:
            uri = f"/artemis/api/resource/v1/person/personId/{person_id}/personInfo"
            resp = session._make_request('POST', uri, data={})
            data = resp.json()
            self.stdout.write("/artemis/api/resource/v1/person/personId/{personId}/personInfo:")
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data'):
                person_data = data.get('data', {})
                self.stdout.write(self.style.SUCCESS(f"Персона найдена: {person_data.get('personName')}"))
                self.stdout.write(f"Организация: {person_data.get('orgIndexCode')}, Начало доступа: {person_data.get('beginTime')}, Конец доступа: {person_data.get('endTime')}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/resource/v1/person/personId/{{personId}}/personInfo error: {e}"))

        # 3) Проверка лиц персоны через FRS API
        try:
            payload = {
                'pageNo': 1,
                'pageSize': 10,
                'resourceType': 'person',
                'resourceIndexCode': person_id
            }
            resp = session._make_request('POST', '/artemis/api/frs/v1/face/picture', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/frs/v1/face/picture:")
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data'):
                self.stdout.write(self.style.SUCCESS("Фото лица найдено"))
            else:
                self.stdout.write(self.style.WARNING("Фото лица не найдено или недоступно"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/frs/v1/face/picture error: {e}"))

        # 4) Проверка разрешений на доступ через ACS API
        try:
            payload = {
                'pageNo': 1, 
                'pageSize': 10,
                'personId': person_id
            }
            resp = session._make_request('POST', '/artemis/api/acs/v1/auth/config/search', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/acs/v1/auth/config/search:")
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data', {}).get('total', 0) > 0:
                self.stdout.write(self.style.SUCCESS(f"Найдено разрешений на доступ: {data.get('data', {}).get('total', 0)}"))
            else:
                self.stdout.write(self.style.WARNING("Разрешения на доступ не найдены"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/acs/v1/auth/config/search error: {e}"))

        # 5) Проверка статуса применения доступа на устройства
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            start_time = (now - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
            end_time = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
            
            payload = {
                'pageNo': 1,
                'pageSize': 10,
                'personId': person_id,
                'startTime': start_time,
                'endTime': end_time,
                'applicationResultType': 0  # 0-все, 1-успех, 2-неудача
            }
            resp = session._make_request('POST', '/artemis/api/acs/v1/auth/applicationResult', data=payload)
            data = resp.json()
            self.stdout.write("/artemis/api/acs/v1/auth/applicationResult:")
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data', {}).get('total', 0) > 0:
                self.stdout.write(self.style.SUCCESS(f"Найдено записей применения: {data.get('data', {}).get('total', 0)}"))
                items = data.get('data', {}).get('list', [])
                for item in items:
                    status = "Успех" if item.get('resultCode') == 1 else "Ошибка"
                    self.stdout.write(f"Устройство: {item.get('deviceName')}, Статус: {status}, Время: {item.get('timeStamp')}")
            else:
                self.stdout.write(self.style.WARNING("Записи о применении прав не найдены"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"/artemis/api/acs/v1/auth/applicationResult error: {e}"))

        self.stdout.write(self.style.SUCCESS("Проверка завершена (Resource API + ACS API)"))