# egov_integration/management/commands/setup_egov_settings.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from egov_integration.models import EgovSettings
from cryptography.fernet import Fernet
from django.conf import settings
import base64


class Command(BaseCommand):
    help = 'Настройка начальных параметров для интеграции с egov.kz'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-key',
            type=str,
            help='API ключ для egov.kz'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='https://api.egov.kz',
            help='Базовый URL API egov.kz'
        )
        parser.add_argument(
            '--admin-user',
            type=str,
            help='Имя администратора для записи настроек'
        )

    def handle(self, *args, **options):
        self.stdout.write('Настройка интеграции с egov.kz...')
        
        # Получаем пользователя-администратора
        admin_user = None
        if options['admin_user']:
            try:
                admin_user = User.objects.get(username=options['admin_user'])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Пользователь {options["admin_user"]} не найден')
                )
        
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        # Создаем базовые настройки
        settings_data = [
            {
                'name': 'EGOV_BASE_URL',
                'value': options['base_url'],
                'description': 'Базовый URL API egov.kz',
                'is_encrypted': False
            },
            {
                'name': 'EGOV_TIMEOUT',
                'value': '30',
                'description': 'Таймаут запросов к API (в секундах)',
                'is_encrypted': False
            },
            {
                'name': 'EGOV_MAX_RETRIES',
                'value': '3',
                'description': 'Максимальное количество повторов запроса',
                'is_encrypted': False
            },
            {
                'name': 'EGOV_RATE_LIMIT_PER_MINUTE',
                'value': '60',
                'description': 'Лимит запросов в минуту',
                'is_encrypted': False
            },
            {
                'name': 'EGOV_CACHE_TTL_SECONDS',
                'value': '300',
                'description': 'Время кеширования результатов (в секундах)',
                'is_encrypted': False
            }
        ]
        
        # Добавляем API ключ, если предоставлен
        if options['api_key']:
            api_key_encrypted = self._encrypt_value(options['api_key'])
            settings_data.append({
                'name': 'EGOV_API_KEY',
                'value': api_key_encrypted,
                'description': 'API ключ для доступа к egov.kz (зашифрован)',
                'is_encrypted': True
            })
        
        # Создаем или обновляем настройки
        created_count = 0
        updated_count = 0
        
        for setting_data in settings_data:
            setting, created = EgovSettings.objects.update_or_create(
                name=setting_data['name'],
                defaults={
                    'value': setting_data['value'],
                    'description': setting_data['description'],
                    'is_encrypted': setting_data['is_encrypted'],
                    'updated_by': admin_user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Создана настройка: {setting.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⚠ Обновлена настройка: {setting.name}')
                )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Настройка завершена! Создано: {created_count}, обновлено: {updated_count}'
            )
        )
        
        if not options['api_key']:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    'ВНИМАНИЕ: API ключ не был предоставлен. '
                    'Добавьте его через Django Admin или повторно запустите команду с --api-key'
                )
            )
        
        self.stdout.write('')
        self.stdout.write('Следующие шаги:')
        self.stdout.write('1. Получите API ключ на портале egov.kz')
        self.stdout.write('2. Добавьте его в настройки через Django Admin или переменную окружения EGOV_API_KEY')
        self.stdout.write('3. Настройте права доступа для пользователей')
        self.stdout.write('4. Протестируйте интеграцию: /egov/ajax/health/')

    def _encrypt_value(self, value):
        """Шифрование значения с помощью ключа из настроек"""
        try:
            key = getattr(settings, 'IIN_ENCRYPTION_KEY', '')
            if not key:
                self.stdout.write(
                    self.style.ERROR('IIN_ENCRYPTION_KEY не настроен в settings')
                )
                return value
            
            f = Fernet(key.encode())
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка шифрования: {e}')
            )
            return value
