"""
Management command для обновления организации у существующих гостей в HCP.
Применяет orgIndexCode из настроек HIKCENTRAL_DEFAULT_ORG_INDEX или HIKCENTRAL_ORG_NAME
ко всем гостям, зарегистрированным в системе.

Использование:
    python manage.py update_guests_organization [--dry-run] [--force]

Параметры:
    --dry-run: Показать что будет изменено без реального применения
    --force: Обновить организацию даже если она уже установлена
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from visitors.models import Guest
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession, find_org_by_name

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Обновляет организацию у существующих гостей в HCP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без реального применения',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Обновить организацию даже если она уже установлена',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ (--dry-run): изменения не будут применены'))

        # Получаем HikCentral сервер
        try:
            hik_server = HikCentralServer.objects.filter(enabled=True).first()
            if not hik_server:
                self.stdout.write(self.style.ERROR('Ошибка: Не найден активный HikCentral сервер'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении HikCentral сервера: {e}'))
            return

        # Создаём сессию
        session = HikCentralSession(hik_server)
        
        # Определяем целевую организацию
        default_org = getattr(settings, 'HIKCENTRAL_DEFAULT_ORG_INDEX', '1')
        org_name = getattr(settings, 'HIKCENTRAL_ORG_NAME', '')
        
        if org_name:
            self.stdout.write(f'Поиск организации "{org_name}" в HCP...')
            found_org = find_org_by_name(session, org_name)
            if found_org:
                default_org = found_org
                self.stdout.write(self.style.SUCCESS(f'[OK] Найдена организация "{org_name}" с orgIndexCode={default_org}'))
            else:
                self.stdout.write(self.style.WARNING(f'[!] Организация "{org_name}" не найдена, используется orgIndexCode={default_org}'))
        else:
            self.stdout.write(f'Используется orgIndexCode={default_org} из настроек')

        # Получаем всех гостей с hikcentral_person_id
        guests = Guest.objects.exclude(hikcentral_person_id__isnull=True).exclude(hikcentral_person_id='')
        total_guests = guests.count()
        
        if total_guests == 0:
            self.stdout.write(self.style.WARNING('Не найдено гостей с hikcentral_person_id'))
            return

        self.stdout.write(f'Найдено гостей для обработки: {total_guests}')
        
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for i, guest in enumerate(guests, 1):
            person_id = guest.hikcentral_person_id
            guest_name = f"{guest.last_name} {guest.first_name}"
            
            self.stdout.write(f'\n[{i}/{total_guests}] Обработка: {guest_name} (personId={person_id})')

            try:
                # Получаем текущую информацию о госте в HCP
                lookup_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
                    'personId': str(person_id)
                })
                lookup_json = lookup_resp.json()

                if not (isinstance(lookup_json, dict) and lookup_json.get('code') == '0' and lookup_json.get('data')):
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Гость не найден в HCP: {lookup_json.get("msg", "Unknown error")}'))
                    error_count += 1
                    continue

                person_data = lookup_json['data']
                current_org = person_data.get('orgIndexCode', '')

                # Проверяем, нужно ли обновлять
                if current_org == default_org and not force:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Организация уже установлена: {current_org}'))
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(self.style.WARNING(f'  [DRY-RUN] Изменение: {current_org} → {default_org}'))
                    updated_count += 1
                    continue

                # Обновляем организацию
                update_payload = {
                    'personId': str(person_id),
                    'personName': person_data.get('personName', guest_name),
                    'orgIndexCode': default_org,
                }
                
                # Сохраняем существующие даты если они есть
                if person_data.get('beginTime'):
                    update_payload['beginTime'] = person_data['beginTime']
                if person_data.get('endTime'):
                    update_payload['endTime'] = person_data['endTime']

                update_resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/update', data=update_payload)
                update_json = update_resp.json()

                if isinstance(update_json, dict) and update_json.get('code') == '0':
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Обновлено: {current_org} -> {default_org}'))
                    updated_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Ошибка обновления: {update_json.get("msg", "Unknown error")}'))
                    error_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Ошибка: {e}'))
                logger.exception(f'Error updating organization for guest {person_id}')
                error_count += 1

        # Итоги
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'ИТОГИ:'))
        self.stdout.write(f'  Всего гостей: {total_guests}')
        self.stdout.write(self.style.SUCCESS(f'  Обновлено: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'  Пропущено: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'  Ошибок: {error_count}'))
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('Это был тестовый запуск. Запустите без --dry-run для применения изменений.'))

