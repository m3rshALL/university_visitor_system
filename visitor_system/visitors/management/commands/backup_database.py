"""
Management command для создания резервной копии базы данных.

Usage:
    python manage.py backup_database
    python manage.py backup_database --output /path/to/backup.json
    python manage.py backup_database --s3  # Upload to S3 if configured
"""

import os
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Создание резервной копии базы данных в JSON формате'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Путь к файлу backup (по умолчанию: backups/backup_YYYYMMDD_HHMMSS.json)',
        )
        parser.add_argument(
            '--s3',
            action='store_true',
            help='Загрузить backup в S3 после создания',
        )
        parser.add_argument(
            '--keep-local',
            action='store_true',
            help='Сохранить локальную копию при загрузке в S3',
        )

    def handle(self, *args, **options):
        """Создание backup базы данных."""
        try:
            # Генерация имени файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if options['output']:
                backup_file = options['output']
            else:
                # Создаём директорию backups если её нет
                backup_dir = os.path.join(settings.BASE_DIR, 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
            
            self.stdout.write(self.style.NOTICE(f'Создание backup: {backup_file}'))
            
            # Создание backup через dumpdata
            with open(backup_file, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--exclude=contenttypes',
                    '--exclude=auth.permission',
                    '--indent=2',
                    stdout=f
                )
            
            # Проверка размера файла
            file_size = os.path.getsize(backup_file)
            file_size_mb = file_size / (1024 * 1024)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Backup успешно создан: {backup_file} ({file_size_mb:.2f} MB)'
                )
            )
            logger.info(f'Database backup created: {backup_file} ({file_size_mb:.2f} MB)')
            
            # Загрузка в S3 если требуется
            if options['s3']:
                success = self._upload_to_s3(backup_file, timestamp)
                
                # Удаляем локальную копию если загрузка успешна и не требуется её сохранение
                if success and not options['keep_local']:
                    os.remove(backup_file)
                    self.stdout.write(
                        self.style.SUCCESS('Локальная копия удалена после загрузки в S3')
                    )
            
            return f'Backup created: {backup_file}'
            
        except Exception as e:
            error_msg = f'Ошибка при создании backup: {str(e)}'
            logger.error(error_msg, exc_info=True)
            raise CommandError(error_msg)
    
    def _upload_to_s3(self, backup_file, timestamp):
        """Загрузка backup в S3."""
        try:
            # Проверяем наличие настроек S3
            if not hasattr(settings, 'AWS_S3_BACKUP_BUCKET'):
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  AWS_S3_BACKUP_BUCKET не настроен. Пропускаем загрузку в S3.'
                    )
                )
                return False
            
            # Импортируем boto3 только если нужна загрузка
            try:
                import boto3
                from botocore.exceptions import ClientError
            except ImportError:
                self.stdout.write(
                    self.style.ERROR(
                        '❌ boto3 не установлен. Установите: pip install boto3'
                    )
                )
                return False
            
            self.stdout.write(self.style.NOTICE('Загрузка в S3...'))
            
            # Создание S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            )
            
            # Имя файла в S3
            s3_key = f'backups/backup_{timestamp}.json'
            
            # Загрузка
            s3_client.upload_file(
                backup_file,
                settings.AWS_S3_BACKUP_BUCKET,
                s3_key,
                ExtraArgs={'ServerSideEncryption': 'AES256'}  # Encryption at rest
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Backup загружен в S3: s3://{settings.AWS_S3_BACKUP_BUCKET}/{s3_key}'
                )
            )
            logger.info(f'Backup uploaded to S3: {s3_key}')
            
            return True
            
        except Exception as e:
            error_msg = f'Ошибка при загрузке в S3: {str(e)}'
            logger.error(error_msg, exc_info=True)
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            return False

