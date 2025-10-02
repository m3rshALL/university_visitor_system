"""
Management command для проверки наличия фото у Person в HCP.

Использование:
    python manage.py verify_person_photo <person_id>
"""
import logging
from django.core.management.base import BaseCommand
from hikvision_integration.models import HikCentralServer
from hikvision_integration.services import HikCentralSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Проверяет наличие фото у Person в HikCentral Professional'

    def add_arguments(self, parser):
        parser.add_argument(
            'person_id',
            type=str,
            help='Person ID в HCP для проверки',
        )

    def handle(self, *args, **options):
        person_id = options.get('person_id')

        self.stdout.write('=' * 80)
        self.stdout.write(f'Проверка фото для Person ID: {person_id}')
        self.stdout.write('=' * 80)

        # Получаем HikCentral сервер
        try:
            hik_server = HikCentralServer.objects.filter(enabled=True).first()
            if not hik_server:
                self.stdout.write(self.style.ERROR('Ошибка: Не найден активный HikCentral сервер'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при получении HikCentral сервера: {e}'))
            return

        try:
            session = HikCentralSession(hik_server)
            
            # Получаем информацию о Person
            self.stdout.write('\n1. Получение информации о Person...')
            person_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
                'personId': str(person_id)
            })
            person_json = person_resp.json()
            
            if not (isinstance(person_json, dict) and person_json.get('code') == '0'):
                self.stdout.write(self.style.ERROR(f'Ошибка: {person_json.get("msg", "Unknown error")}'))
                return
            
            person_data = person_json.get('data', {})
            
            self.stdout.write(self.style.SUCCESS('[OK] Person найден'))
            self.stdout.write(f'  Имя: {person_data.get("personName", "N/A")}')
            self.stdout.write(f'  personCode: {person_data.get("personCode", "N/A")}')
            self.stdout.write(f'  orgIndexCode: {person_data.get("orgIndexCode", "N/A")}')
            
            # Проверяем наличие фото
            has_photo = person_data.get('personPhoto')
            has_photo_url = person_data.get('photoUrl')
            
            self.stdout.write(f'\n2. Проверка фото:')
            if has_photo:
                self.stdout.write(self.style.SUCCESS(f'  [OK] personPhoto: присутствует ({len(has_photo)} символов base64)'))
            else:
                self.stdout.write(self.style.WARNING('  [!] personPhoto: отсутствует'))
                
            if has_photo_url:
                self.stdout.write(self.style.SUCCESS(f'  [OK] photoUrl: {has_photo_url}'))
            else:
                self.stdout.write(self.style.WARNING('  [!] photoUrl: отсутствует'))
            
            # Проверяем faces (массив лиц)
            faces = person_data.get('faces', [])
            if faces:
                self.stdout.write(self.style.SUCCESS(f'\n  [OK] faces: найдено {len(faces)} лиц'))
                for i, face in enumerate(faces, 1):
                    self.stdout.write(f'    Face {i}:')
                    self.stdout.write(f'      faceId: {face.get("faceId", "N/A")}')
                    self.stdout.write(f'      faceUrl: {face.get("faceUrl", "N/A")}')
            else:
                self.stdout.write(self.style.WARNING('  [!] faces: массив пустой'))
            
            # Поиск в Face Library
            self.stdout.write(f'\n3. Поиск в Face Library...')
            try:
                # Получаем список face groups
                groups_resp = session._make_request('POST', '/artemis/api/frs/v1/face/groupList', data={
                    'pageNo': 1,
                    'pageSize': 100
                })
                groups_json = groups_resp.json()
                
                if isinstance(groups_json, dict) and groups_json.get('code') == '0':
                    groups = groups_json.get('data', {}).get('list', [])
                    self.stdout.write(f'  Найдено Face Groups: {len(groups)}')
                    
                    for group in groups:
                        group_code = group.get('indexCode', group.get('faceGroupIndexCode'))
                        group_name = group.get('name', 'N/A')
                        
                        # Ищем faces в этой группе
                        try:
                            faces_resp = session._make_request('POST', '/artemis/api/frs/v1/face', data={
                                'faceGroupIndexCode': group_code,
                                'pageNo': 1,
                                'pageSize': 100
                            })
                            faces_json = faces_resp.json()
                            
                            if isinstance(faces_json, dict) and faces_json.get('code') == '0':
                                face_list = faces_json.get('data', {}).get('list', [])
                                # Ищем наш personId
                                our_faces = [f for f in face_list if str(f.get('personId')) == str(person_id)]
                                if our_faces:
                                    self.stdout.write(self.style.SUCCESS(f'\n  [OK] Найдено {len(our_faces)} лиц в группе "{group_name}" (indexCode: {group_code})'))
                                    for face in our_faces:
                                        self.stdout.write(f'    - faceId: {face.get("faceId", "N/A")}')
                                        self.stdout.write(f'      faceUrl: {face.get("faceUrl", "N/A")}')
                        except Exception:
                            pass
                            
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  [!] Не удалось проверить Face Library: {e}'))
            
            # Итоги
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write('ИТОГИ:')
            
            if has_photo or has_photo_url or faces:
                self.stdout.write(self.style.SUCCESS('[OK] У Person есть фото в HCP'))
                if not has_photo_url:
                    self.stdout.write(self.style.WARNING('\n[!] НО photoUrl отсутствует - фото может не отображаться в UI'))
                    self.stdout.write('Попробуйте:')
                    self.stdout.write('  1. Применить права через auth/reapplication')
                    self.stdout.write('  2. Обновить страницу в HCP UI')
                    self.stdout.write('  3. Проверить размер фото (минимум 200x200 рекомендуется)')
            else:
                self.stdout.write(self.style.ERROR('[ERROR] У Person НЕТ фото в HCP'))
                self.stdout.write('\nВозможные причины:')
                self.stdout.write('  1. Фото слишком маленькое (72x72) - попробуйте загрузить фото побольше')
                self.stdout.write('  2. Формат фото не поддерживается')
                self.stdout.write('  3. API вернул Success, но фото не сохранилось')
            
            self.stdout.write('\n' + '=' * 80)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))
            logger.exception('Error verifying person photo')

