from django.core.management.base import BaseCommand
from hikvision_integration.models import HikPersonBinding
from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer


class Command(BaseCommand):
    help = "Проверка гостя в HikCentral по корректным API из документации"

    def add_arguments(self, parser):
        parser.add_argument("guest_id", type=int, help="ID гостя в системе (personCode)")

    def handle(self, *args, **options):
        guest_id = options["guest_id"]
        binding = HikPersonBinding.objects.filter(guest_id=guest_id).first()
        if not binding:
            self.stdout.write(self.style.ERROR(f"Binding для guest_id={guest_id} не найден"))
            return

        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            self.stdout.write(self.style.ERROR("HikCentralServer не настроен или выключен"))
            return
        
        session = HikCentralSession(server)
        person_code = str(guest_id)
        person_id = binding.person_id
        
        self.stdout.write(self.style.NOTICE(f"Проверка гостя: guest_id={guest_id}, person_code={person_code}, person_id={person_id}"))
        
        # 1. Проверка по personCode (точное соответствие)
        self.stdout.write("\n=== Проверка по personCode ===")
        try:
            resp = session._make_request('POST', '/artemis/api/resource/v1/person/personCode/personInfo', 
                                        data={'personCode': person_code})
            data = resp.json()
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data'):
                person_data = data.get('data', {})
                self.stdout.write(self.style.SUCCESS(f"Персона найдена: {person_data.get('personName')}"))
                self.stdout.write(f"ID: {person_data.get('personId')}, Код: {person_data.get('personCode')}")
                self.stdout.write(f"Организация: {person_data.get('orgIndexCode')}")
                self.stdout.write(f"Начало доступа: {person_data.get('beginTime')}")
                self.stdout.write(f"Конец доступа: {person_data.get('endTime')}")
            else:
                self.stdout.write(self.style.WARNING("Персона не найдена по коду"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            
        # 2. Проверка по personId (точное соответствие)
        self.stdout.write("\n=== Проверка по personId ===")
        try:
            resp = session._make_request('POST', f'/artemis/api/resource/v1/person/personId/{person_id}/personInfo', 
                                        data={})
            data = resp.json()
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data'):
                person_data = data.get('data', {})
                self.stdout.write(self.style.SUCCESS(f"Персона найдена: {person_data.get('personName')}"))
                self.stdout.write(f"ID: {person_data.get('personId')}, Код: {person_data.get('personCode')}")
            else:
                self.stdout.write(self.style.WARNING("Персона не найдена по ID"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            
        # 3. Поиск через advance/personList с параметрами
        self.stdout.write("\n=== Поиск персоны через advance/personList ===")
        try:
            resp = session._make_request('POST', '/artemis/api/resource/v1/person/advance/personList', 
                                        data={
                                            'pageNo': 1,
                                            'pageSize': 10,
                                            'personCode': person_code,  # Точное значение personCode
                                            'personId': person_id       # Точное значение personId
                                        })
            data = resp.json()
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data', {}).get('list'):
                persons = data.get('data', {}).get('list', [])
                for p in persons:
                    self.stdout.write(self.style.SUCCESS(f"Найдена персона: {p.get('personName')}"))
                    self.stdout.write(f"ID: {p.get('personId')}, Код: {p.get('personCode')}")
            else:
                self.stdout.write(self.style.WARNING("Персона не найдена в результатах поиска"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            
        # 4. Проверка лица через FRS API
        self.stdout.write("\n=== Проверка лица через FRS API ===")
        try:
            resp = session._make_request('POST', '/artemis/api/frs/v1/face/picture', 
                                        data={
                                            'pageNo': 1,
                                            'pageSize': 10,
                                            'resourceType': 'person',
                                            'resourceIndexCode': person_id
                                        })
            data = resp.json()
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data', {}).get('list'):
                faces = data.get('data', {}).get('list', [])
                for face in faces:
                    self.stdout.write(self.style.SUCCESS(f"Найдено фото лица: {face.get('faceGroupName')}"))
            else:
                self.stdout.write(self.style.WARNING("Фото лица не найдено"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            
        # 5. Проверка доступа через ACS API
        self.stdout.write("\n=== Проверка прав доступа через ACS API ===")
        try:
            resp = session._make_request('POST', '/artemis/api/acs/v1/auth/config/search', 
                                        data={
                                            'pageNo': 1,
                                            'pageSize': 10,
                                            'personIds': [person_id]
                                        })
            data = resp.json()
            self.stdout.write(str(data))
            
            if data.get('code') == '0' and data.get('data', {}).get('list'):
                configs = data.get('data', {}).get('list', [])
                for config in configs:
                    self.stdout.write(self.style.SUCCESS(f"Найдена настройка доступа: {config.get('authConfigName')}"))
                    self.stdout.write(f"Персона: {config.get('personName')}")
                    self.stdout.write(f"Начало: {config.get('startTime')}, Окончание: {config.get('endTime')}")
            else:
                self.stdout.write(self.style.WARNING("Настройки доступа не найдены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            
        self.stdout.write(self.style.SUCCESS("\nПроверка завершена"))