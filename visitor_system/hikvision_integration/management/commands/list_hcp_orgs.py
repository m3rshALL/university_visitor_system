"""
Management command для просмотра всех организаций в HikCentral Professional.

Использование:
    python manage.py list_hcp_orgs
"""
import logging
from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Показывает список всех организаций в HikCentral Professional'

    def handle(self, *args, **options):
        self.stdout.write('Получение списка организаций из HCP...')
        self.stdout.write('=' * 80)

        # Получаем HikCentral сервер
        try:
            hik_server = HikCentralServer.objects.filter(enabled=True).first()
            if not hik_server:
                all_servers = HikCentralServer.objects.all()
                if all_servers.exists():
                    self.stdout.write(self.style.ERROR('Ошибка: Найдены серверы, но все отключены'))
                    for server in all_servers:
                        self.stdout.write(f'  - {server.name}: enabled={server.enabled}')
                    self.stdout.write('\nВключите сервер через админ-панель Django')
                else:
                    self.stdout.write(self.style.ERROR('Ошибка: Не найден HikCentral сервер'))
                    self.stdout.write('Создайте HikCentral сервер через админ-панель Django')
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении HikCentral сервера: {e}'))
            logger.exception('Error getting HikCentral server')
            return

        self.stdout.write(f'Используется сервер: {hik_server.name}')
        self.stdout.write(f'URL: {hik_server.base_url}')
        self.stdout.write('')

        # Получаем список организаций
        try:
            session = HikCentralSession(hik_server)
            
            # Запрашиваем все организации
            payload = {
                'pageNo': 1,
                'pageSize': 100
            }
            
            self.stdout.write('Отправка запроса к HCP API...')
            resp = session._make_request('POST', '/artemis/api/resource/v1/org/advance/orgList', data=payload)
            result = resp.json()
            
            if isinstance(result, dict) and result.get('code') == '0':
                orgs = result.get('data', {}).get('list', [])
                total = result.get('data', {}).get('total', 0)
                
                if not orgs:
                    self.stdout.write(self.style.WARNING('Организации не найдены'))
                    return
                
                self.stdout.write(self.style.SUCCESS(f'\nНайдено организаций: {total}'))
                self.stdout.write('=' * 80)
                
                for i, org in enumerate(orgs, 1):
                    org_index = org.get('orgIndexCode', org.get('indexCode', 'N/A'))
                    org_name = org.get('orgName', 'N/A')
                    parent_index = org.get('parentOrgIndexCode', 'N/A')
                    
                    self.stdout.write(f'\n[{i}] {org_name}')
                    self.stdout.write(f'    orgIndexCode: {org_index}')
                    self.stdout.write(f'    parentOrgIndexCode: {parent_index}')
                    
                    # Дополнительная информация если есть
                    if org.get('orgPath'):
                        self.stdout.write(f'    Путь: {org.get("orgPath")}')
                
                self.stdout.write('\n' + '=' * 80)
                
                # Проверяем наличие "Visitor Management"
                visitor_mgmt = [org for org in orgs if 'visitor' in org.get('orgName', '').lower() and 'manage' in org.get('orgName', '').lower()]
                
                if visitor_mgmt:
                    self.stdout.write(self.style.SUCCESS('\n[OK] Найдены организации, похожие на "Visitor Management":'))
                    for org in visitor_mgmt:
                        self.stdout.write(f'  - {org.get("orgName")} (orgIndexCode: {org.get("orgIndexCode", org.get("indexCode"))})')
                else:
                    self.stdout.write(self.style.WARNING('\n[!] Не найдена организация "Visitor Management"'))
                    self.stdout.write('  Создайте её в HikCentral Professional или измените HIKCENTRAL_ORG_NAME')
                
            else:
                self.stdout.write(self.style.ERROR(f'Ошибка API: {result.get("msg", "Unknown error")}'))
                self.stdout.write(f'Код ошибки: {result.get("code")}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении списка организаций: {e}'))
            logger.exception('Error fetching organizations')
            self.stdout.write('\nПроверьте:')
            self.stdout.write('  - Корректность HIKCENTRAL_BASE_URL')
            self.stdout.write('  - Правильность HIKCENTRAL_INTEGRATION_KEY и SECRET')
            self.stdout.write('  - Доступность сервера HCP')

