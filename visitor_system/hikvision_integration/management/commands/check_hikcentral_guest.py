"""
Script to check and verify presence of a guest in HikCentral by guest ID
"""
from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer, HikPersonBinding
from hikvision_integration.services import HikCentralSession
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Проверяет наличие гостя в HikCentral Professional"

    def add_arguments(self, parser):
        parser.add_argument("guest_id", type=int, help="ID гостя в системе")

    def handle(self, *args, **options):
        guest_id = options['guest_id']
        
        # Получаем binding для гостя из базы данных
        binding = HikPersonBinding.objects.filter(guest_id=guest_id).first()
        if not binding:
            self.stdout.write(self.style.ERROR(f"Binding не найден для guest_id={guest_id}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Найден binding: guest_id={binding.guest_id}, person_id={binding.person_id}, status={binding.status}"))
        
        # Получаем сервер HikCentral
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            self.stdout.write(self.style.ERROR("HikCentralServer не настроен или выключен"))
            return
            
        session = HikCentralSession(server)
        
        # Методы поиска персоны в HikCentral
        person_code = str(guest_id)
        person_id = binding.person_id
        
        # Метод 1: Поиск через personCode/personInfo
        self.stdout.write("\nМетод 1: Поиск по personCode")
        lookup_data = {"personCode": person_code}
        lookup_resp = session._make_request(
            'POST', 
            '/artemis/api/resource/v1/person/personCode/personInfo', 
            data=lookup_data
        )
        lookup_json = lookup_resp.json() if lookup_resp.status_code == 200 else None
        self.stdout.write(json.dumps(lookup_json, indent=2, ensure_ascii=False))
        
        # Метод 2: Поиск в списке персон
        self.stdout.write("\nМетод 2: Поиск через personList")
        search_data = {
            "pageNo": 1,
            "pageSize": 10,
            "personCode": person_code
        }
        search_resp = session._make_request(
            'POST', 
            '/artemis/api/resource/v1/person/personList', 
            data=search_data
        )
        search_json = search_resp.json() if search_resp.status_code == 200 else None
        
        if search_json and search_json.get('code') == '0' and search_json.get('data'):
            total = search_json['data'].get('total', 0)
            self.stdout.write(f"Найдено результатов: {total}")
            
            if total > 0:
                person_list = search_json['data'].get('list', [])
                for person in person_list:
                    if person.get('personCode') == person_code or person.get('personId') == person_id:
                        self.stdout.write(self.style.SUCCESS(f"Найдена персона: ID={person.get('personId')}, Name={person.get('personName')}"))
                        self.stdout.write(json.dumps(person, indent=2, ensure_ascii=False))
                        return
        
        # Метод 3: Расширенный поиск персоны
        self.stdout.write("\nМетод 3: Расширенный поиск")
        adv_search_data = {
            "pageNo": 1,
            "pageSize": 10,
            "personIdList": [person_id]  # Используем ID из binding
        }
        adv_resp = session._make_request(
            'POST', 
            '/artemis/api/resource/v1/person/advance/personList', 
            data=adv_search_data
        )
        adv_json = adv_resp.json() if adv_resp.status_code == 200 else None
        
        if adv_json and adv_json.get('code') == '0' and adv_json.get('data'):
            total = adv_json['data'].get('total', 0)
            self.stdout.write(f"Найдено результатов по ID: {total}")
            
            if total > 0:
                person_list = adv_json['data'].get('list', [])
                for person in person_list:
                    self.stdout.write(self.style.SUCCESS(f"Найдена персона: ID={person.get('personId')}, Name={person.get('personName')}"))
                    self.stdout.write(json.dumps(person, indent=2, ensure_ascii=False))
                    return
        
        self.stdout.write(self.style.ERROR("Персона НЕ найдена в HikCentral Professional!"))