"""
Management команда для просмотра Face Groups в HikCentral Professional
"""
from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession


class Command(BaseCommand):
    help = 'Список Face Groups в HikCentral Professional'

    def handle(self, *args, **options):
        print("=" * 80)
        print("FACE GROUPS В HIKCENTRAL PROFESSIONAL")
        print("=" * 80)
        
        # Получаем активный сервер
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            print("\n[ERROR] HikCentral сервер не найден или отключен")
            return
        
        print(f"\n[OK] Сервер: {server.name}")
        print(f"URL: {server.base_url}")
        
        try:
            session = HikCentralSession(server)
            print("[OK] Сессия создана")
            
            # Получаем список Face Groups
            print("\n" + "-" * 80)
            print("Запрос списка Face Groups...")
            print("-" * 80)
            
            resp = session._make_request('POST', '/artemis/api/frs/v1/face/groupList', data={
                'pageNo': 1,
                'pageSize': 100
            })
            
            json_data = resp.json()
            
            if json_data.get('code') != '0':
                print(f"\n[ERROR] Ошибка API: {json_data.get('msg')}")
                return
            
            data = json_data.get('data', {})
            groups = data.get('list', [])
            total = data.get('total', 0)
            
            print(f"\n[OK] Найдено Face Groups: {total}")
            
            if not groups:
                print("\n[INFO] Face Groups не найдены")
                print("\nСистема автоматически создаст Face Group 'Guests' при первой загрузке фото")
            else:
                print("\n" + "=" * 80)
                print("СПИСОК FACE GROUPS")
                print("=" * 80)
                
                for i, group in enumerate(groups, 1):
                    print(f"\n{i}. {group.get('groupName', 'N/A')}")
                    print(f"   Group ID: {group.get('groupId')}")
                    print(f"   Type: {group.get('groupType', 'N/A')}")
                    print(f"   Face Count: {group.get('faceCount', 0)}")
                    if group.get('remark'):
                        print(f"   Remark: {group.get('remark')}")
            
            # Проверяем наличие группы "Guests"
            print("\n" + "=" * 80)
            guests_group = next((g for g in groups if g.get('groupName') == 'Guests'), None)
            
            if guests_group:
                print("[OK] Face Group 'Guests' найдена")
                print(f"   Group ID: {guests_group.get('groupId')}")
                print(f"   Лиц в группе: {guests_group.get('faceCount', 0)}")
                print("\n[OK] Система готова для автоматической загрузки фото")
            else:
                print("[INFO] Face Group 'Guests' не найдена")
                print("Будет создана автоматически при первой загрузке фото")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"\n[ERROR] Ошибка: {e}")
            import traceback
            traceback.print_exc()

