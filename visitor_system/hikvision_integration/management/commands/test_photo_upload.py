"""
Management command для тестирования загрузки фото гостя в HCP.

Использование:
    python manage.py test_photo_upload <guest_id>
    python manage.py test_photo_upload --last  # последний гость с фото
"""
import logging
from django.core.management.base import BaseCommand
from visitors.models import Guest
from hikvision_integration.models import HikCentralServer, HikPersonBinding
from hikvision_integration.services import HikCentralSession, upload_face_hikcentral

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирует загрузку фото гостя в HikCentral Professional'

    def add_arguments(self, parser):
        parser.add_argument(
            'guest_id',
            nargs='?',
            type=int,
            help='ID гостя для тестирования загрузки фото',
        )
        parser.add_argument(
            '--last',
            action='store_true',
            help='Использовать последнего гостя с фото',
        )

    def handle(self, *args, **options):
        from visitors.models import GuestEntry, GroupGuest
        
        guest_id = options.get('guest_id')
        use_last = options.get('last')

        # Получаем гостя
        if use_last:
            # Ищем гостя с привязкой к HCP (у которого есть hikcentral_person_id)
            binding = HikPersonBinding.objects.exclude(person_id='').order_by('-created_at').first()
            if not binding:
                self.stdout.write(self.style.ERROR('Ошибка: Не найдено гостей привязанных к HCP'))
                self.stdout.write('Сначала зарегистрируйте гостя через систему')
                return
            try:
                guest = Guest.objects.get(id=binding.guest_id)
            except Guest.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Ошибка: Гость с ID={binding.guest_id} не найден'))
                return
            self.stdout.write(f'Используется последний гость привязанный к HCP: {guest.full_name} (ID={guest.id})')
        elif guest_id:
            try:
                guest = Guest.objects.get(id=guest_id)
            except Guest.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Ошибка: Гость с ID={guest_id} не найден'))
                return
        else:
            self.stdout.write(self.style.ERROR('Ошибка: Укажите guest_id или используйте --last'))
            self.stdout.write('Использование: python manage.py test_photo_upload <guest_id>')
            self.stdout.write('Или: python manage.py test_photo_upload --last')
            return

        # Проверяем привязку к HCP
        binding = HikPersonBinding.objects.filter(guest_id=guest.id).first()
        if not binding:
            self.stdout.write(self.style.WARNING('Предупреждение: Гость не привязан к HCP'))
            self.stdout.write('  Сначала зарегистрируйте гостя через систему')
            return

        person_id = binding.person_id

        # Ищем фото гостя в разных местах (GuestEntry, GroupGuest, GuestInvitation)
        photo_path = None
        photo_source = None
        
        # 1. Проверяем GuestEntry
        guest_entry = GuestEntry.objects.filter(iin=guest.iin).exclude(photo__isnull=True).exclude(photo='').first()
        if guest_entry and getattr(guest_entry.photo, 'path', None):
            photo_path = guest_entry.photo.path
            photo_source = f'GuestEntry (приглашение)'
            
        # 2. Проверяем GroupGuest
        if not photo_path:
            # Пробуем найти через ИИН или ФИО
            group_guest = None
            if guest.iin:
                group_guest = GroupGuest.objects.filter(iin_hash=guest.iin_hash).exclude(photo__isnull=True).exclude(photo='').first()
            if not group_guest:
                group_guest = GroupGuest.objects.filter(full_name=guest.full_name).exclude(photo__isnull=True).exclude(photo='').first()
            if group_guest and getattr(group_guest.photo, 'path', None):
                photo_path = group_guest.photo.path
                photo_source = f'GroupGuest (групповое приглашение)'

        self.stdout.write('=' * 80)
        self.stdout.write(f'Тестирование загрузки фото для гостя:')
        self.stdout.write(f'  ID: {guest.id}')
        self.stdout.write(f'  ФИО: {guest.full_name}')
        self.stdout.write(f'  HCP Person ID: {person_id}')
        self.stdout.write(f'  Фото: {photo_path or "не найдено"}')
        if photo_source:
            self.stdout.write(f'  Источник: {photo_source}')
        self.stdout.write('=' * 80)

        # Проверяем наличие фото
        if not photo_path:
            self.stdout.write(self.style.ERROR('\nОшибка: У гостя нет загруженного фото'))
            self.stdout.write('  Фото должно быть загружено при регистрации через систему')
            self.stdout.write('  Проверьте GuestEntry или GroupGuest в базе данных')
            return

        # Получаем HikCentral сервер
        try:
            hik_server = HikCentralServer.objects.filter(enabled=True).first()
            if not hik_server:
                self.stdout.write(self.style.ERROR('Ошибка: Не найден активный HikCentral сервер'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении HikCentral сервера: {e}'))
            return

        self.stdout.write(f'\nHikCentral сервер: {hik_server.name}')
        self.stdout.write(f'Base URL: {hik_server.base_url}')
        self.stdout.write('')

        # Читаем фото
        try:
            with open(photo_path, 'rb') as f:
                image_bytes = f.read()
            self.stdout.write(f'Фото загружено: {len(image_bytes)} байт')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при чтении фото: {e}'))
            logger.exception('Error reading photo')
            return

        # Тестируем загрузку
        try:
            self.stdout.write('\nЗапуск загрузки фото в HCP...')
            self.stdout.write('-' * 80)
            
            session = HikCentralSession(hik_server)
            
            # Вызываем upload_face_hikcentral
            face_id = upload_face_hikcentral(
                session,
                face_lib_id='',  # auto-detect
                image_bytes=image_bytes,
                person_id=person_id
            )
            
            self.stdout.write('-' * 80)
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Загрузка завершена!'))
            self.stdout.write(f'  Face ID: {face_id}')
            self.stdout.write('')
            self.stdout.write('Проверьте логи для детальной информации:')
            self.stdout.write('  tail -f logs/visitor_system.log | Select-String "HikCentral.*face"')
            self.stdout.write('')
            self.stdout.write('Проверьте в HikCentral Professional:')
            self.stdout.write(f'  1. Откройте Person Management')
            self.stdout.write(f'  2. Найдите Person ID: {person_id}')
            self.stdout.write(f'  3. Проверьте наличие фото в профиле')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Ошибка при загрузке фото: {e}'))
            logger.exception('Error uploading photo')
            self.stdout.write('')
            self.stdout.write('Проверьте логи для детальной информации:')
            self.stdout.write('  tail -n 100 logs/visitor_system.log')

        self.stdout.write('\n' + '=' * 80)

