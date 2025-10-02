"""
Management command для тестирования поиска организации в HCP.

Использование:
    python manage.py test_org_lookup [--org-name "Название организации"]
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession, find_org_by_name

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирует поиск организации в HikCentral Professional'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-name',
            type=str,
            help='Название организации для поиска (по умолчанию из настроек)',
        )

    def handle(self, *args, **options):
        org_name = options.get('org_name') or getattr(settings, 'HIKCENTRAL_ORG_NAME', '')
        
        if not org_name:
            self.stdout.write(self.style.ERROR('Ошибка: Не указано название организации'))
            self.stdout.write('Использование: python manage.py test_org_lookup --org-name "Название"')
            self.stdout.write('Или установите HIKCENTRAL_ORG_NAME в .env файле')
            return

        self.stdout.write(f'Поиск организации: "{org_name}"')
        self.stdout.write('=' * 60)

        # Получаем HikCentral сервер
        try:
            hik_server = HikCentralServer.objects.filter(enabled=True).first()
            if not hik_server:
                # Проверяем, есть ли вообще серверы
                all_servers = HikCentralServer.objects.all()
                if all_servers.exists():
                    self.stdout.write(self.style.ERROR('Ошибка: Найдены серверы, но все отключены'))
                    self.stdout.write('Включите HikCentral сервер через админ-панель Django')
                else:
                    self.stdout.write(self.style.ERROR('Ошибка: Не найден HikCentral сервер'))
                    self.stdout.write('Создайте HikCentral сервер через админ-панель Django')
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении HikCentral сервера: {e}'))
            return

        self.stdout.write(f'Используется HikCentral сервер: {hik_server.name}')
        self.stdout.write(f'Base URL: {hik_server.base_url}')
        self.stdout.write('')

        # Создаём сессию и ищем организацию
        try:
            session = HikCentralSession(hik_server)
            
            self.stdout.write('Отправка запроса к HCP API...')
            org_index = find_org_by_name(session, org_name)
            
            if org_index:
                self.stdout.write(self.style.SUCCESS('[OK] УСПЕХ: Организация найдена!'))
                self.stdout.write('')
                self.stdout.write(f'  Название: {org_name}')
                self.stdout.write(f'  orgIndexCode: {org_index}')
                self.stdout.write('')
                self.stdout.write('Этот orgIndexCode будет использоваться для всех новых гостей.')
                self.stdout.write('')
                
                # Показываем текущие настройки
                default_org = getattr(settings, 'HIKCENTRAL_DEFAULT_ORG_INDEX', '1')
                force_org = getattr(settings, 'HIKCENTRAL_FORCE_ORG', False)
                
                self.stdout.write('Текущие настройки:')
                self.stdout.write(f'  HIKCENTRAL_DEFAULT_ORG_INDEX: {default_org}')
                self.stdout.write(f'  HIKCENTRAL_FORCE_ORG: {force_org}')
                self.stdout.write(f'  HIKCENTRAL_ORG_NAME: {getattr(settings, "HIKCENTRAL_ORG_NAME", "")}')
                
                if org_index != default_org:
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING(f'[!] Обратите внимание: найденный orgIndexCode ({org_index}) отличается от HIKCENTRAL_DEFAULT_ORG_INDEX ({default_org})'))
                    self.stdout.write('  Система будет использовать найденный orgIndexCode из HIKCENTRAL_ORG_NAME.')
                
            else:
                self.stdout.write(self.style.ERROR(f'[ERROR] Организация "{org_name}" не найдена в HCP'))
                self.stdout.write('')
                self.stdout.write('Возможные причины:')
                self.stdout.write('  1. Организация с таким именем не существует в HCP')
                self.stdout.write('  2. Проверьте точное написание (включая регистр и пробелы)')
                self.stdout.write('  3. У Integration Partner нет доступа к этой организации')
                self.stdout.write('')
                self.stdout.write('Что делать:')
                self.stdout.write('  - Создайте организацию в HikCentral Professional')
                self.stdout.write('  - Или используйте HIKCENTRAL_DEFAULT_ORG_INDEX с известным ID')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] ОШИБКА подключения: {e}'))
            self.stdout.write('')
            self.stdout.write('Проверьте:')
            self.stdout.write('  - HIKCENTRAL_BASE_URL правильный')
            self.stdout.write('  - HIKCENTRAL_INTEGRATION_KEY и SECRET корректны')
            self.stdout.write('  - Сервер HCP доступен')
            logger.exception('Error during organization lookup')

