"""
Management command для проверки настроек HikCentral Professional.

Использование:
    python manage.py check_hcp_setup
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from hikvision_integration.models import HikCentralServer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Проверяет настройки подключения к HikCentral Professional'

    def handle(self, *args, **options):
        self.stdout.write('Проверка настроек HikCentral Professional')
        self.stdout.write('=' * 80)
        
        # 1. Проверка настроек в .env
        self.stdout.write('\n1. Настройки из .env:')
        self.stdout.write('-' * 80)
        
        settings_to_check = [
            ('HIKCENTRAL_BASE_URL', getattr(settings, 'HIKCENTRAL_BASE_URL', None)),
            ('HIKCENTRAL_INTEGRATION_KEY', getattr(settings, 'HIKCENTRAL_INTEGRATION_KEY', None)),
            ('HIKCENTRAL_INTEGRATION_SECRET', getattr(settings, 'HIKCENTRAL_INTEGRATION_SECRET', None)),
            ('HIKCENTRAL_DEFAULT_ORG_INDEX', getattr(settings, 'HIKCENTRAL_DEFAULT_ORG_INDEX', None)),
            ('HIKCENTRAL_FORCE_ORG', getattr(settings, 'HIKCENTRAL_FORCE_ORG', None)),
            ('HIKCENTRAL_ORG_NAME', getattr(settings, 'HIKCENTRAL_ORG_NAME', None)),
        ]
        
        missing_settings = []
        for name, value in settings_to_check:
            if value:
                # Скрываем чувствительные данные
                if 'SECRET' in name or 'PASSWORD' in name:
                    display_value = '***' + str(value)[-4:] if len(str(value)) > 4 else '****'
                else:
                    display_value = value
                self.stdout.write(f'  [OK] {name}: {display_value}')
            else:
                self.stdout.write(self.style.WARNING(f'  [!] {name}: не установлен'))
                missing_settings.append(name)
        
        if missing_settings:
            self.stdout.write(self.style.WARNING(f'\n[!] Не установлены настройки: {", ".join(missing_settings)}'))
        
        # 2. Проверка сервера в базе данных
        self.stdout.write('\n2. HikCentral серверы в базе данных:')
        self.stdout.write('-' * 80)
        
        try:
            all_servers = HikCentralServer.objects.all()
            
            if not all_servers.exists():
                self.stdout.write(self.style.ERROR('  [ERROR] Не найдено ни одного сервера'))
                self.stdout.write('\n  Создайте сервер через:')
                self.stdout.write('    - Админ-панель Django: /admin/hikvision_integration/hikcentralserver/')
                self.stdout.write('    - Или выполните: python manage.py shell')
                self.stdout.write('      >>> from hikvision_integration.models import HikCentralServer')
                self.stdout.write('      >>> server = HikCentralServer.objects.create(')
                self.stdout.write('      ...     name="Main HCP Server",')
                self.stdout.write('      ...     base_url="https://your-hcp-server.com",')
                self.stdout.write('      ...     integration_key="your_key",')
                self.stdout.write('      ...     integration_secret="your_secret",')
                self.stdout.write('      ...     username="admin",')
                self.stdout.write('      ...     password="your_password",')
                self.stdout.write('      ...     enabled=True')
                self.stdout.write('      ... )')
                return
            
            enabled_count = all_servers.filter(enabled=True).count()
            disabled_count = all_servers.filter(enabled=False).count()
            
            self.stdout.write(f'  Всего серверов: {all_servers.count()}')
            self.stdout.write(f'  Включено: {enabled_count}')
            self.stdout.write(f'  Отключено: {disabled_count}')
            self.stdout.write('')
            
            for server in all_servers:
                status = '[ON] ВКЛЮЧЕН' if server.enabled else '[OFF] ОТКЛЮЧЕН'
                style = self.style.SUCCESS if server.enabled else self.style.WARNING
                self.stdout.write(style(f'  {status}: {server.name}'))
                self.stdout.write(f'    URL: {server.base_url}')
                self.stdout.write(f'    Integration Key: {server.integration_key}')
                self.stdout.write(f'    Username: {server.username}')
                self.stdout.write('')
            
            if enabled_count == 0:
                self.stdout.write(self.style.WARNING('  [!] Все серверы отключены'))
                self.stdout.write('    Включите сервер через админ-панель Django')
            elif enabled_count > 1:
                self.stdout.write(self.style.WARNING(f'  [!] Включено несколько серверов ({enabled_count})'))
                self.stdout.write('    Будет использован первый найденный')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Ошибка при получении серверов: {e}'))
            logger.exception('Error checking servers')
        
        # 3. Рекомендации
        self.stdout.write('\n3. Следующие шаги:')
        self.stdout.write('-' * 80)
        
        if not all_servers.exists() or enabled_count == 0:
            self.stdout.write('  1. Создайте/включите HikCentral сервер в базе данных')
        else:
            self.stdout.write('  1. [OK] Сервер настроен')
            self.stdout.write('  2. Проверьте список организаций:')
            self.stdout.write('       python manage.py list_hcp_orgs')
            self.stdout.write('  3. Найдите нужную организацию:')
            self.stdout.write('       python manage.py test_org_lookup')
            self.stdout.write('  4. Обновите существующих гостей (если нужно):')
            self.stdout.write('       python manage.py update_guests_organization --dry-run')
        
        self.stdout.write('\n' + '=' * 80)

