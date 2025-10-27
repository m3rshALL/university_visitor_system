from celery import shared_task
import logging
from django.utils import timezone
from django.conf import settings
from .models import HikAccessTask, HikDevice, HikPersonBinding, HikCentralServer
from .services import (
    HikSession,
    ensure_person,
    upload_face,
    assign_access,
    revoke_access,
    HikCentralSession,
    ensure_person_hikcentral,
    upload_face_hikcentral,
)


logger = logging.getLogger(__name__)


def _get_device_session(device: HikDevice) -> HikSession:
    return HikSession(device)


def _get_hikcentral_server():
    """Получает активный HikCentral сервер для создания сессии.
    
    Возвращает server object вместо сессии, чтобы сессию можно было
    создать в контексте 'with' statement для автоматического закрытия.
    
    Returns:
        HikCentralServer instance или None
    """
    return HikCentralServer.objects.filter(enabled=True).first()


@shared_task(queue='hikvision')
def enroll_face_task(task_id: int) -> None:
    task = HikAccessTask.objects.filter(id=task_id).first()
    if not task:
        return
    logger.info("Hik enroll_face_task start: task_id=%s", task_id)
    task.status = 'running'
    task.attempts += 1
    task.save(update_fields=['status', 'attempts'])
    try:
        device = task.device or HikDevice.objects.filter(
            enabled=True, is_primary=True
        ).first()
        if not device:
            raise RuntimeError('No active HikDevice configured')
        logger.info(
            "Hik enroll: using device id=%s name=%s",
            getattr(device, 'id', None),
            getattr(device, 'name', None),
        )
        hc_server = _get_hikcentral_server()
        logger.info("Hik enroll: hc_server=%s", bool(hc_server))
        session = _get_device_session(device)
        payload = task.payload or {}
        employee_no = str(
            payload.get('employee_no') or payload.get('guest_id') or task.guest_id
        )
        name = payload.get('name') or 'Guest'
        # Период доступа по умолчанию: сейчас до +1 день
        valid_from = payload.get('valid_from') or timezone.now().isoformat()
        valid_to = payload.get('valid_to') or (
            timezone.now() + timezone.timedelta(days=1)
        ).isoformat()
        face_lib_id = payload.get('face_lib_id') or getattr(
            settings, 'HIKCENTRAL_FACE_GROUP_INDEX_CODE', '1'
        )
        # Получаем фото, если оно было передано явно в payload
        image_bytes = payload.get('image_bytes')
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('utf-8')
        # Если фото не передали, пробуем взять из Guest.photo
        if not image_bytes and (task.guest_id or payload.get('guest_id')):
            try:
                from visitors.models import Guest
                g = Guest.objects.filter(
                    id=(task.guest_id or payload.get('guest_id'))
                ).first()
                if g and getattr(g, 'photo', None) and getattr(g.photo, 'path', None):
                    with open(g.photo.path, 'rb') as f:
                        image_bytes = f.read()
                        logger.info(
                            'Hik enroll: loaded image from guest.photo (%s bytes)',
                            len(image_bytes),
                        )
            except Exception:
                logger.exception('Hik enroll: failed to load guest.photo')

        # Фоллбэк: если фото всё ещё нет, пробуем взять из GuestInvitation.guest_photo
        if not image_bytes:
            logger.info(
                'Hik enroll: Attempting to load photo from GuestInvitation '
                '(task_id=%s, visit_id=%s, guest_id=%s)',
                task_id, task.visit_id, task.guest_id
            )
            try:
                from visitors.models import GuestInvitation
                inv = None
                if task.visit_id:
                    inv = GuestInvitation.objects.filter(visit_id=task.visit_id).first()
                    logger.info(
                        'Hik enroll: GuestInvitation search by visit_id=%s: %s',
                        task.visit_id, 'found' if inv else 'NOT FOUND'
                    )
                if not inv and (task.guest_id or payload.get('guest_id')):
                    gid = task.guest_id or payload.get('guest_id')
                    inv = GuestInvitation.objects.filter(
                        visit__guest_id=gid
                    ).first()
                    logger.info(
                        'Hik enroll: GuestInvitation search by guest_id=%s: %s',
                        gid, 'found' if inv else 'NOT FOUND'
                    )
                
                if inv:
                    has_photo_field = hasattr(inv, 'guest_photo')
                    photo_obj = getattr(inv, 'guest_photo', None) if has_photo_field else None
                    logger.info(
                        'Hik enroll: GuestInvitation.guest_photo field exists: %s, value: %s',
                        has_photo_field, bool(photo_obj)
                    )
                    
                    photo_path = getattr(photo_obj, 'path', None) if photo_obj else None
                    logger.info(
                        'Hik enroll: Photo path: %s',
                        photo_path if photo_path else 'NO PATH'
                    )
                    
                    if photo_path:
                        import os
                        file_exists = os.path.exists(photo_path)
                        logger.info(
                            'Hik enroll: Photo file exists on disk: %s (path=%s)',
                            file_exists, photo_path
                        )
                        
                        if file_exists:
                            with open(photo_path, 'rb') as f:
                                image_bytes = f.read()
                                logger.info(
                                    'Hik enroll: ✅ Successfully loaded invitation photo (%s bytes)',
                                    len(image_bytes),
                                )
                        else:
                            logger.error(
                                'Hik enroll: ❌ Photo file does NOT exist on disk: %s',
                                photo_path
                            )
                else:
                    logger.warning(
                        'Hik enroll: ❌ GuestInvitation NOT FOUND for visit_id=%s, guest_id=%s',
                        task.visit_id, task.guest_id
                    )
            except Exception:
                logger.exception('Hik enroll: ❌ Exception while loading invitation.guest_photo')

        logger.info(
            "Hik enroll: ensure_person start employee_no=%s name=%s",
            employee_no,
            name,
        )
        
        # Используем context manager для автоматического закрытия сессии
        if hc_server:
            with HikCentralSession(hc_server) as hc_session:
                # Через HCP: создаём/обновляем персону; используем personCode=employee_no,
                # получаем реальный personId
                person_id = ensure_person_hikcentral(
                    hc_session,
                    employee_no,
                    name,
                    valid_from,
                    valid_to,
                )
        else:
            person_id = ensure_person(session, employee_no, name, valid_from, valid_to)
        logger.info("Hik enroll: ensure_person done person_id=%s", person_id)

        # Проверка статуса image_bytes ПЕРЕД загрузкой
        if image_bytes:
            logger.info(
                "Hik enroll: ✅ Photo available for upload (%s bytes)",
                len(image_bytes)
            )
        else:
            logger.warning(
                "Hik enroll: ⚠️ NO PHOTO available for task_id=%s, "
                "visit_id=%s, guest_id=%s. Person will be created WITHOUT photo.",
                task_id, task.visit_id, task.guest_id
            )

        face_id = ''
        if image_bytes:
            logger.info("Hik enroll: upload_face start")
            
            # ГИБРИДНЫЙ ПОДХОД: Person через HCP, Face через ISAPI
            # Это обходит проблему с Face Group в HCP
            use_isapi_for_face = getattr(settings, 'HIKCENTRAL_USE_ISAPI_FOR_FACE', False)
            
            if use_isapi_for_face and hc_server:
                # Person создан в HCP, но фото загружаем НАПРЯМУЮ на устройства через ISAPI
                logger.info("Hik enroll: Using HYBRID approach - face via ISAPI to all devices")
                try:
                    from .services import upload_face_isapi
                    
                    # Загружаем фото на ВСЕ активные устройства
                    all_devices = HikDevice.objects.filter(enabled=True)
                    success_count = 0
                    
                    for dev in all_devices:
                        logger.info(f"Hik enroll: Uploading face to device {dev.name} ({dev.host})")
                        try:
                            if upload_face_isapi(dev, employee_no, image_bytes):
                                success_count += 1
                                logger.info(f"Hik enroll: Successfully uploaded to {dev.name}")
                            else:
                                logger.warning(f"Hik enroll: Failed to upload to {dev.name}")
                        except Exception as e:
                            logger.error(f"Hik enroll: Error uploading to {dev.name}: {e}")
                    
                    logger.info(f"Hik enroll: ISAPI upload completed - {success_count}/{all_devices.count()} devices")
                    face_id = f'isapi_{employee_no}'  # Фиктивный face_id для логирования
                    
                except Exception as e:
                    logger.error("Hik enroll: ISAPI face upload failed: %s", e)
                    # Если ISAPI не работает, можем попробовать HCP (хотя он не работает)
                    face_id = ''
                    
            elif hc_server:
                # HCP JSON upload (оптимизированный метод) с context manager
                try:
                    with HikCentralSession(hc_server) as hc_session:
                        face_id = upload_face_hikcentral(
                            hc_session,
                            face_lib_id,
                            image_bytes,
                            person_id,
                        )
                        logger.info("Hik enroll: Upload result: %s", face_id)
                except Exception as e:
                    logger.error("Hik enroll: HCP upload failed: %s", e)
                    face_id = ''
            else:
                # Полностью ISAPI подход (старый код)
                try:
                    face_id = upload_face(session, face_lib_id, image_bytes, person_id)
                except Exception as e:
                    logger.error("Hik enroll: ISAPI face upload failed: %s", e)
                    face_id = ''
            
            logger.info("Hik enroll: upload_face done face_id=%s", face_id)
        # Двери по умолчанию — из конфигурации устройства
        door_ids = payload.get('door_ids') or (
            device.doors_json if isinstance(device.doors_json, list) else []
        )
        logger.info("Hik enroll: assign/reapply start doors=%s", door_ids)
        # Для HikCentral reapplication выполняется в assign_access_level_task
        # Для legacy ISAPI назначаем доступ напрямую
        if not hc_session:
            assign_access(session, person_id, door_ids, valid_from, valid_to)
        logger.info("Hik enroll: assign/reapply done")

        HikPersonBinding.objects.update_or_create(
            guest_id=task.guest_id or 0,
            device=device,
            defaults={
                'person_id': person_id,
                'face_id': face_id,
                'access_from': valid_from,
                'access_to': valid_to,
                'status': 'active',
                'last_error': '',
            }
        )
        logger.info("Hik enroll: binding saved for guest_id=%s", task.guest_id)
        
        # КРИТИЧЕСКИЙ FIX: Сохраняем person_id в Visit для мониторинга проходов
        if task.visit_id:
            try:
                from visitors.models import Visit
                Visit.objects.filter(id=task.visit_id).update(
                    hikcentral_person_id=str(person_id)
                )
                logger.info(
                    "Hik enroll: Visit %s updated with person_id=%s",
                    task.visit_id, person_id
                )
            except Exception as e:
                logger.warning("Hik enroll: Failed to update Visit.person_id: %s", e)
        
        task.status = 'success'
        task.last_error = ''
        task.save(update_fields=['status', 'last_error'])
        logger.info("Hik enroll_face_task success: task_id=%s", task_id)
    except Exception as e:
        task.status = 'failed'
        task.last_error = str(e)
        task.save(update_fields=['status', 'last_error'])
        logger.exception("Hik enroll_face_task failed: task_id=%s error=%s", task_id, e)


@shared_task(queue='hikvision')
def revoke_access_task(task_id: int) -> None:
    task = HikAccessTask.objects.filter(id=task_id).first()
    if not task:
        return
    task.status = 'running'
    task.attempts += 1
    task.save(update_fields=['status', 'attempts'])
    try:
        device = task.device or HikDevice.objects.filter(
            enabled=True, is_primary=True
        ).first()
        if not device:
            raise RuntimeError('No active HikDevice configured')
        hc_server = _get_hikcentral_server()
        session = _get_device_session(device)
        payload = task.payload or {}
        person_id = payload.get('person_id') or ''
        if not person_id:
            binding = HikPersonBinding.objects.filter(
                guest_id=task.guest_id, device=device
            ).first()
            if binding:
                person_id = binding.person_id
        if not person_id:
            raise RuntimeError('person_id not found for revoke')
        door_ids = payload.get('door_ids') or (
            device.doors_json if isinstance(device.doors_json, list) else []
        )
        # Для HikCentral отзыв выполняется в revoke_access_level_task
        # Для legacy ISAPI отзываем доступ напрямую
        if not hc_server:
            revoke_access(session, person_id, door_ids)
        HikPersonBinding.objects.filter(
            guest_id=task.guest_id, device=device
        ).update(status='revoked')
        task.status = 'success'
        task.last_error = ''
        task.save(update_fields=['status', 'last_error'])
    except Exception as e:
        task.status = 'failed'
        task.last_error = str(e)
        task.save(update_fields=['status', 'last_error'])


@shared_task(bind=True, queue='hikvision', max_retries=5, default_retry_delay=60)
def assign_access_level_task(self, task_id: int) -> None:
    """
    Назначает гостю access level group после успешной загрузки фото.
    
    Логика:
    1. Получает person_id из task.payload или guest.hikcentral_person_id
    2. Назначает access level group (из settings.HIKCENTRAL_GUEST_ACCESS_GROUP_ID)
    3. Применяет настройки на устройства через reapplication API
    
    FIX #3: Добавлен retry mechanism с exponential backoff:
    - max_retries=5 (до 5 попыток)
    - backoff: 60s → 120s → 240s → 480s → 960s
    """
    from django.conf import settings
    from .services import assign_access_level_to_person
    
    task = HikAccessTask.objects.filter(id=task_id).first()
    if not task:
        logger.warning("assign_access_level_task: task %s not found", task_id)
        return
    
    logger.info("HikCentral: assign_access_level_task start for task_id=%s", task_id)
    
    task.status = 'running'
    task.attempts += 1
    task.save(update_fields=['status', 'attempts'])
    
    try:
        hc_server = _get_hikcentral_server()
        if not hc_server:
            raise RuntimeError('No HikCentral server available')
        
        # Получаем person_id
        payload = task.payload or {}
        person_id = payload.get('person_id')
        
        # Если person_id нет в payload - пробуем получить из Guest
        if not person_id and task.guest_id:
            try:
                from visitors.models import Guest
                guest = Guest.objects.filter(id=task.guest_id).first()
                if guest and hasattr(guest, 'hikcentral_person_id'):
                    person_id = guest.hikcentral_person_id
            except Exception as e:
                logger.warning("Failed to get person_id from Guest: %s", e)
        
        # Если person_id нет - пробуем из Visit
        if not person_id and task.visit_id:
            try:
                from visitors.models import Visit
                visit = Visit.objects.select_related('guest').filter(
                    id=task.visit_id
                ).first()
                # FIX: person_id хранится в Visit.hikcentral_person_id, а НЕ в Guest!
                if visit and visit.hikcentral_person_id:
                    person_id = visit.hikcentral_person_id
                    logger.info(
                        "HikCentral: Found person_id=%s from Visit.hikcentral_person_id",
                        person_id
                    )
            except Exception as e:
                logger.warning("Failed to get person_id from Visit: %s", e)
        
        if not person_id:
            raise RuntimeError(
                f'person_id not found for task {task_id}, '
                f'guest_id={task.guest_id}, visit_id={task.visit_id}'
            )
        
        # Используем context manager для сессии HikCentral
        with HikCentralSession(hc_server) as hc_session:
            # FIX #10: Проверяем существование и validity персоны перед назначением доступа
            from .services import get_person_hikcentral
            from datetime import datetime
            
            person_info = get_person_hikcentral(hc_session, str(person_id))
            
            if not person_info:
                raise RuntimeError(
                    f'Person {person_id} not found in HikCentral. '
                    f'Cannot assign access level.'
                )
            
            # Проверяем validity персоны
            person_status = person_info.get('status')
            person_end_time = person_info.get('endTime')
            
            # FIX: status может отсутствовать в API response - проверяем только если есть
            if person_status is not None and person_status != 1:
                raise RuntimeError(
                    f'Person {person_id} is not active (status={person_status}). '
                    f'Cannot assign access level.'
                )
            
            # Проверяем, что персона не истекла
            if person_end_time:
                try:
                    from dateutil.parser import parse
                    end_datetime = parse(person_end_time)
                    from django.utils import timezone
                    if timezone.is_naive(end_datetime):
                        end_datetime = timezone.make_aware(end_datetime)
                    
                    now = timezone.now()
                    if end_datetime < now:
                        raise RuntimeError(
                            f'Person {person_id} validity expired at {person_end_time}. '
                            f'Cannot assign access level.'
                        )
                except Exception as parse_exc:
                    logger.warning(
                        "Could not parse person endTime %s: %s",
                        person_end_time, parse_exc
                    )
            
            # Логируем результат проверки
            if person_status is None:
                logger.info(
                    "HikCentral: Person %s validation passed "
                    "(status not returned by API, endTime=%s)",
                    person_id, person_end_time
                )
            else:
                logger.info(
                    "HikCentral: Person %s validation passed (status=%s, endTime=%s)",
                    person_id, person_status, person_end_time
                )
            
            # Получаем access_group_id из settings
            access_group_id = getattr(
                settings,
                'HIKCENTRAL_GUEST_ACCESS_GROUP_ID',
                '7'  # Default: "Visitors Access"
            )
            
            logger.info(
                "HikCentral: Assigning access group %s to person %s",
                access_group_id, person_id
            )
            
            # Назначаем access level
            success = assign_access_level_to_person(
                hc_session,
                str(person_id),
                str(access_group_id),
                access_type=1  # Access Control type
            )
        
        if not success:
            raise RuntimeError('Failed to assign access level')
        
        task.status = 'success'
        task.last_error = ''
        task.save(update_fields=['status', 'last_error'])
        
        # FIX #13: Метрики Prometheus
        try:
            from .metrics import hikcentral_access_assignments_total
            hikcentral_access_assignments_total.labels(status='success').inc()
        except Exception:
            pass
        
        # Помечаем Visit как access_granted=True
        if task.visit_id:
            try:
                from visitors.models import Visit
                Visit.objects.filter(id=task.visit_id).update(access_granted=True)
                logger.info(
                    "HikCentral: Visit %s marked as access_granted=True",
                    task.visit_id
                )
            except Exception as e:
                logger.warning("Failed to update Visit.access_granted: %s", e)
        
        logger.info(
            "HikCentral: Successfully assigned access level to person %s",
            person_id
        )
        
    except Exception as exc:
        error_msg = f"Failed to assign access level: {exc}"
        logger.error("HikCentral: %s", error_msg)
        task.status = 'failed'
        task.last_error = error_msg
        task.save(update_fields=['status', 'last_error'])
        
        # FIX #13: Метрики Prometheus
        try:
            from .metrics import hikcentral_access_assignments_total
            hikcentral_access_assignments_total.labels(status='failed').inc()
        except Exception:
            pass
        
        # FIX #3: Retry с exponential backoff
        if self.request.retries < self.max_retries:
            # Exponential backoff: 60s, 120s, 240s, 480s, 960s
            countdown = 60 * (2 ** self.request.retries)
            logger.warning(
                "HikCentral: Retrying assign_access_level_task in %ds "
                "(attempt %d/%d)",
                countdown, self.request.retries + 1, self.max_retries
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                "HikCentral: Max retries reached for assign_access_level_task, "
                "task_id=%s",
                task_id
            )
        import traceback
        traceback.print_exc()


@shared_task(bind=True, queue='hikvision', max_retries=3, default_retry_delay=30)
def revoke_access_level_task(self, visit_id: int) -> None:
    """
    FIX #4: Отзывает access level у гостя при закрытии/отмене визита.
    
    Логика:
    1. Получает Visit по visit_id
    2. Извлекает person_id из visit.hikcentral_person_id или guest.hikcentral_person_id
    3. Отзывает access level через revoke_access_level_from_person()
    4. Помечает visit.access_revoked=True
    
    Retry mechanism:
    - max_retries=3 (до 3 попыток)
    - backoff: 30s → 60s → 120s
    """
    from django.conf import settings
    from .services import revoke_access_level_from_person
    
    try:
        from visitors.models import Visit
        visit = Visit.objects.select_related('guest').filter(
            id=visit_id
        ).first()
        
        if not visit:
            logger.warning("revoke_access_level_task: Visit %s not found", visit_id)
            return
        
        # Проверяем, что доступ был выдан и ещё не отозван
        if not visit.access_granted:
            logger.info(
                "revoke_access_level_task: Visit %s has no access granted, skipping",
                visit_id
            )
            return
        
        if visit.access_revoked:
            logger.info(
                "revoke_access_level_task: Visit %s access already revoked, skipping",
                visit_id
            )
            return
        
        # Получаем person_id
        person_id = visit.hikcentral_person_id
        if not person_id and visit.guest:
            person_id = getattr(visit.guest, 'hikcentral_person_id', None)
        
        if not person_id:
            logger.warning(
                "revoke_access_level_task: No person_id found for visit %s",
                visit_id
            )
            return
        
        # Получаем HikCentral server
        hc_server = _get_hikcentral_server()
        if not hc_server:
            raise RuntimeError('No HikCentral server available')
        
        # Получаем access_group_id
        access_group_id = getattr(
            settings,
            'HIKCENTRAL_GUEST_ACCESS_GROUP_ID',
            '7'
        )
        
        logger.info(
            "HikCentral: Revoking access group %s from person %s (visit %s)",
            access_group_id, person_id, visit_id
        )
        
        # Отзываем access level с использованием context manager
        with HikCentralSession(hc_server) as hc_session:
            success = revoke_access_level_from_person(
                hc_session,
                str(person_id),
                str(access_group_id),
                access_type=1
            )
        
        if not success:
            raise RuntimeError('Failed to revoke access level')
        
        # Помечаем visit.access_revoked=True
        visit.access_revoked = True
        visit.save(update_fields=['access_revoked'])
        
        # FIX #13: Метрики Prometheus
        try:
            from .metrics import hikcentral_access_revocations_total
            hikcentral_access_revocations_total.labels(status='success').inc()
        except Exception:
            pass
        
        logger.info(
            "HikCentral: Successfully revoked access for person %s (visit %s)",
            person_id, visit_id
        )
        
    except Exception as exc:
        error_msg = f"Failed to revoke access level: {exc}"
        logger.error("HikCentral: %s", error_msg)
        
        # FIX #13: Метрики Prometheus
        try:
            from .metrics import hikcentral_access_revocations_total
            hikcentral_access_revocations_total.labels(status='failed').inc()
        except Exception:
            pass
        
        # Retry с exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 30 * (2 ** self.request.retries)
            logger.warning(
                "HikCentral: Retrying revoke_access_level_task in %ds "
                "(attempt %d/%d)",
                countdown, self.request.retries + 1, self.max_retries
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                "HikCentral: Max retries reached for revoke_access_level_task, "
                "visit_id=%s",
                visit_id
            )


@shared_task
def monitor_guest_passages_task() -> None:
    """
    Периодическая задача для мониторинга проходов гостей через турникеты.
    
    Логика (Вариант В + Автоматический Check-in/out):
    1. Находит все активные визиты с access_granted=True и access_revoked=False
    2. Для каждого визита запрашивает события проходов за последние 5 минут
    3. Обновляет счётчики входов/выходов
    4. АВТОМАТИЧЕСКИЙ CHECK-IN: При первом ВХОДЕ через турникет
       - Меняет статус EXPECTED → CHECKED_IN
       - Устанавливает entry_time
    5. АВТОМАТИЧЕСКИЙ CHECKOUT: При первом ВЫХОДЕ через турникет
       - Меняет статус CHECKED_IN → CHECKED_OUT
       - Устанавливает exit_time
       - Отзывает доступ через revoke_access_level_from_person()
       - Помечает access_revoked=True
    
    Запускается каждые 5 минут через Celery Beat.
    """
    from django.conf import settings
    from datetime import timedelta
    from .services import get_door_events, revoke_access_level_from_person
    
    logger.info("HikCentral: monitor_guest_passages_task started")
    
    try:
        from visitors.models import Visit
        
        # Получаем активные визиты с предоставленным доступом
        active_visits = Visit.objects.filter(
            access_granted=True,
            access_revoked=False,
            status__in=['EXPECTED', 'CHECKED_IN']  # Только активные визиты
        ).select_related('guest')
        
        if not active_visits.exists():
            logger.info("HikCentral: No active visits to monitor")
            return
        
        logger.info("HikCentral: Monitoring %d active visits", active_visits.count())
        
        hc_server = _get_hikcentral_server()
        if not hc_server:
            logger.error("HikCentral: No server available for monitoring")
            return
        
        # Временной диапазон: последние 5 минут (для оперативного авто check-in/out)
        now = timezone.now()
        start_time = now - timedelta(minutes=5)
        
        # Используем context manager для автоматического закрытия сессии
        with HikCentralSession(hc_server) as hc_session:
            # ОПТИМИЗАЦИЯ: Батчинг - ОДИН запрос для ВСЕХ гостей вместо 100-500 запросов
            # Получаем ВСЕ события за последние 5 минут (без фильтра по person_id)
            logger.info("HikCentral: Fetching ALL door events (batched query)")
            all_events_data = get_door_events(
                hc_session,
                person_id=None,  # ← БЕЗ фильтра! Получаем все события
                person_name=None,
                start_time=start_time.isoformat(),
                end_time=now.isoformat(),
                door_index_codes=None,
                event_type=None,
                page_no=1,
                page_size=1000  # Увеличенный размер для батчинга
            )
        
        if not all_events_data or 'data' not in all_events_data:
            logger.info("HikCentral: No door events data returned")
            return
        
        all_events = all_events_data['data'].get('list', [])
        logger.info("HikCentral: Received %d total door events", len(all_events))
        
        # Группируем события по personId для быстрого доступа
        events_by_person = {}
        for event in all_events:
            pid = event.get('personId')
            if pid:
                if pid not in events_by_person:
                    events_by_person[pid] = []
                events_by_person[pid].append(event)
        
        logger.info(
            "HikCentral: Events grouped for %d persons",
            len(events_by_person)
        )
        
        # Обрабатываем каждый визит с уже загруженными событиями
        for visit in active_visits:
            try:
                if not visit.hikcentral_person_id:
                    logger.warning(
                        "Visit %s: No hikcentral_person_id",
                        visit.id
                    )
                    continue
                
                person_id = str(visit.hikcentral_person_id)
                
                # Получаем события для этого гостя из предзагруженных данных
                events = events_by_person.get(person_id, [])
                
                if not events:
                    continue
                
                logger.info(
                    "Visit %s: Found %d door events in last 5 minutes",
                    visit.id, len(events)
                )
                
                # Подсчитываем входы и выходы
                new_entries = 0
                new_exits = 0
                first_entry_time = None
                first_exit_time = None
                
                for event in events:
                    event_type = event.get('eventType')
                    event_time_str = event.get('eventTime')
                    
                    if not event_time_str:
                        continue
                    
                    # Парсим время события
                    try:
                        from dateutil.parser import parse
                        event_time = parse(event_time_str)
                        if timezone.is_naive(event_time):
                            event_time = timezone.make_aware(event_time)
                    except Exception as e:
                        logger.warning("Failed to parse event time %s: %s", event_time_str, e)
                        continue
                    
                    # Считаем только события после last check
                    # Чтобы не дублировать подсчёт при повторных запусках
                    last_check = visit.first_exit_detected or visit.first_entry_detected or visit.entry_time
                    if last_check and event_time <= last_check:
                        continue
                    
                    if event_type == 1:  # Вход
                        new_entries += 1
                        if not first_entry_time or event_time < first_entry_time:
                            first_entry_time = event_time
                        # FIX #13: Метрики Prometheus
                        try:
                            from .metrics import hikcentral_door_events_total
                            hikcentral_door_events_total.labels(event_type='entry').inc()
                        except Exception:
                            pass
                    elif event_type == 2:  # Выход
                        new_exits += 1
                        if not first_exit_time or event_time < first_exit_time:
                            first_exit_time = event_time
                        # FIX #13: Метрики Prometheus
                        try:
                            from .metrics import hikcentral_door_events_total
                            hikcentral_door_events_total.labels(event_type='exit').inc()
                        except Exception:
                            pass
                
                # Обновляем счётчики
                if new_entries > 0 or new_exits > 0:
                    visit.entry_count += new_entries
                    visit.exit_count += new_exits
                    
                    # FIX #7: Отправка уведомлений о входе/выходе
                    send_entry_notification = False
                    send_exit_notification = False
                    
                    if first_entry_time and not visit.first_entry_detected:
                        visit.first_entry_detected = first_entry_time
                        send_entry_notification = True
                        logger.info(
                            "Visit %s: First ENTRY detected at %s",
                            visit.id, first_entry_time
                        )
                        
                        # AUTO CHECK-IN: Автоматически меняем статус при входе
                        if visit.status == 'EXPECTED':
                            visit.status = 'CHECKED_IN'
                            visit.entry_time = first_entry_time
                            logger.info(
                                "Visit %s: ✅ Auto check-in via FaceID at %s "
                                "(status: EXPECTED → CHECKED_IN)",
                                visit.id, first_entry_time
                            )
                            
                            # Audit log для автоматического check-in
                            try:
                                from visitors.models import AuditLog
                                AuditLog.objects.create(
                                    action=AuditLog.ACTION_UPDATE,
                                    model='Visit',
                                    object_id=str(visit.pk),
                                    actor=None,
                                    ip_address='127.0.0.1',
                                    user_agent='HikCentral FaceID System',
                                    path='/tasks/monitor-passages',
                                    method='SYSTEM',
                                    changes={
                                        'reason': 'Auto check-in via FaceID turnstile',
                                        'old_status': 'EXPECTED',
                                        'new_status': 'CHECKED_IN',
                                        'entry_time': first_entry_time.isoformat()
                                    }
                                )
                            except Exception as audit_exc:
                                logger.warning(
                                    "Failed to create audit log for auto check-in: %s",
                                    audit_exc
                                )
                    
                    if first_exit_time and not visit.first_exit_detected:
                        visit.first_exit_detected = first_exit_time
                        send_exit_notification = True
                        logger.info(
                            "Visit %s: First EXIT detected at %s",
                            visit.id, first_exit_time
                        )
                        
                        # AUTO CHECKOUT: Автоматически меняем статус при выходе
                        if visit.status == 'CHECKED_IN':
                            visit.status = 'CHECKED_OUT'
                            visit.exit_time = first_exit_time
                            logger.info(
                                "Visit %s: ✅ Auto checkout via FaceID at %s "
                                "(status: CHECKED_IN → CHECKED_OUT)",
                                visit.id, first_exit_time
                            )
                            
                            # Audit log для автоматического checkout
                            try:
                                from visitors.models import AuditLog
                                AuditLog.objects.create(
                                    action=AuditLog.ACTION_UPDATE,
                                    model='Visit',
                                    object_id=str(visit.pk),
                                    actor=None,
                                    ip_address='127.0.0.1',
                                    user_agent='HikCentral FaceID System',
                                    path='/tasks/monitor-passages',
                                    method='SYSTEM',
                                    changes={
                                        'reason': 'Auto checkout via FaceID turnstile',
                                        'old_status': 'CHECKED_IN',
                                        'new_status': 'CHECKED_OUT',
                                        'exit_time': first_exit_time.isoformat()
                                    }
                                )
                            except Exception as audit_exc:
                                logger.warning(
                                    "Failed to create audit log for auto checkout: %s",
                                    audit_exc
                                )
                        elif visit.status == 'EXPECTED':
                            # АНОМАЛИЯ: выход без входа
                            logger.warning(
                                "Visit %s: ⚠️ EXIT detected but status is EXPECTED "
                                "(no entry detected). Possible anomaly or backdoor exit.",
                                visit.id
                            )
                            
                            # Создаем SecurityIncident
                            try:
                                from visitors.models import SecurityIncident
                                incident, created = SecurityIncident.objects.get_or_create(
                                    visit=visit,
                                    incident_type=SecurityIncident.INCIDENT_EXIT_WITHOUT_ENTRY,
                                    defaults={
                                        'description': f'Обнаружен выход через турникет без предварительного входа. '
                                                      f'Exit time: {first_exit_time.strftime("%Y-%m-%d %H:%M:%S")}. '
                                                      f'Возможная аномалия или выход через другой путь.',
                                        'severity': SecurityIncident.SEVERITY_HIGH,
                                        'metadata': {
                                            'exit_time': first_exit_time.isoformat(),
                                            'exit_count': new_exits,
                                            'current_status': visit.status
                                        }
                                    }
                                )
                                if created:
                                    logger.warning(
                                        "Visit %s: SecurityIncident created (EXIT_WITHOUT_ENTRY)",
                                        visit.id
                                    )
                                    # Планируем отправку alert
                                    from .utils import send_security_alert_async
                                    send_security_alert_async(incident.id)
                            except Exception as incident_exc:
                                logger.error(
                                    "Visit %s: Failed to create SecurityIncident: %s",
                                    visit.id, incident_exc
                                )
                    
                    visit.save(update_fields=[
                        'entry_count', 'exit_count',
                        'first_entry_detected', 'first_exit_detected',
                        'status', 'entry_time', 'exit_time'
                    ])
                    
                    logger.info(
                        "Visit %s: Updated counts - entries=%d, exits=%d",
                        visit.id, visit.entry_count, visit.exit_count
                    )
                    
                    # FIX #7: Отправляем уведомления
                    if send_entry_notification and not visit.entry_notification_sent:
                        try:
                            from notifications.tasks import send_passage_notification_task
                            send_passage_notification_task.apply_async(
                                args=[visit.id, 'entry'],
                                countdown=2
                            )
                            visit.entry_notification_sent = True
                            visit.save(update_fields=['entry_notification_sent'])
                            logger.info(
                                "Visit %s: Entry notification scheduled",
                                visit.id
                            )
                        except Exception as notif_exc:
                            logger.warning(
                                "Visit %s: Failed to schedule entry notification: %s",
                                visit.id, notif_exc
                            )
                    
                    if send_exit_notification and not visit.exit_notification_sent:
                        try:
                            from notifications.tasks import send_passage_notification_task
                            send_passage_notification_task.apply_async(
                                args=[visit.id, 'exit'],
                                countdown=2
                            )
                            visit.exit_notification_sent = True
                            visit.save(update_fields=['exit_notification_sent'])
                            logger.info(
                                "Visit %s: Exit notification scheduled",
                                visit.id
                            )
                        except Exception as notif_exc:
                            logger.warning(
                                "Visit %s: Failed to schedule exit notification: %s",
                                visit.id, notif_exc
                            )
                
                # АНОМАЛИЯ: Долгое пребывание (LONG_STAY)
                if visit.status == 'CHECKED_IN' and visit.entry_time:
                    # Проверяем сколько времени гость в здании
                    time_inside = now - visit.entry_time
                    max_stay_hours = getattr(settings, 'MAX_GUEST_STAY_HOURS', 8)
                    
                    if time_inside.total_seconds() > max_stay_hours * 3600:
                        # Гость в здании слишком долго
                        logger.warning(
                            "Visit %s: ⚠️ LONG_STAY detected. Guest inside for %.1f hours",
                            visit.id, time_inside.total_seconds() / 3600
                        )
                        
                        # Проверяем, нет ли уже такого инцидента
                        try:
                            from visitors.models import SecurityIncident
                            incident, created = SecurityIncident.objects.get_or_create(
                                visit=visit,
                                incident_type=SecurityIncident.INCIDENT_LONG_STAY,
                                defaults={
                                    'description': f'Гость находится в здании более {max_stay_hours} часов. '
                                                  f'Entry time: {visit.entry_time.strftime("%Y-%m-%d %H:%M:%S")}. '
                                                  f'Время пребывания: {time_inside.total_seconds() / 3600:.1f} часов.',
                                    'severity': SecurityIncident.SEVERITY_MEDIUM,
                                    'metadata': {
                                        'entry_time': visit.entry_time.isoformat(),
                                        'hours_inside': time_inside.total_seconds() / 3600,
                                        'max_allowed_hours': max_stay_hours
                                    }
                                }
                            )
                            if created:
                                logger.warning(
                                    "Visit %s: SecurityIncident created (LONG_STAY)",
                                    visit.id
                                )
                                # Планируем отправку alert
                                from .utils import send_security_alert_async
                                send_security_alert_async(incident.id)
                        except Exception as incident_exc:
                            logger.error(
                                "Visit %s: Failed to create LONG_STAY incident: %s",
                                visit.id, incident_exc
                            )
                
                # АНОМАЛИЯ: Доступ в нерабочее время (SUSPICIOUS_TIME)
                if visit.status == 'CHECKED_IN' and visit.entry_time:
                    entry_hour = visit.entry_time.hour
                    work_start = getattr(settings, 'WORK_HOURS_START', 6)
                    work_end = getattr(settings, 'WORK_HOURS_END', 22)
                    
                    if entry_hour < work_start or entry_hour >= work_end:
                        # Вход в нерабочее время
                        logger.warning(
                            "Visit %s: ⚠️ SUSPICIOUS_TIME detected. Entry at %02d:00 (work hours: %02d:00-%02d:00)",
                            visit.id, entry_hour, work_start, work_end
                        )
                        
                        try:
                            from visitors.models import SecurityIncident
                            incident, created = SecurityIncident.objects.get_or_create(
                                visit=visit,
                                incident_type=SecurityIncident.INCIDENT_SUSPICIOUS_TIME,
                                defaults={
                                    'description': f'Доступ в нерабочее время ({entry_hour:02d}:00). '
                                                  f'Рабочие часы: {work_start:02d}:00-{work_end:02d}:00. '
                                                  f'Entry time: {visit.entry_time.strftime("%Y-%m-%d %H:%M:%S")}.',
                                    'severity': SecurityIncident.SEVERITY_MEDIUM,
                                    'metadata': {
                                        'entry_time': visit.entry_time.isoformat(),
                                        'entry_hour': entry_hour,
                                        'work_hours': f'{work_start:02d}:00-{work_end:02d}:00'
                                    }
                                }
                            )
                            if created:
                                logger.warning(
                                    "Visit %s: SecurityIncident created (SUSPICIOUS_TIME)",
                                    visit.id
                                )
                                # Планируем отправку alert
                                from .utils import send_security_alert_async
                                send_security_alert_async(incident.id)
                        except Exception as incident_exc:
                            logger.error(
                                "Visit %s: Failed to create SUSPICIOUS_TIME incident: %s",
                                visit.id, incident_exc
                            )
                
                # ВАРИАНТ В: Блокируем после первого выхода
                if visit.first_exit_detected and not visit.access_revoked:
                    logger.info(
                        "Visit %s: First exit detected, revoking access...",
                        visit.id
                    )
                    
                    # Получаем access_group_id из settings
                    access_group_id = getattr(
                        settings,
                        'HIKCENTRAL_GUEST_ACCESS_GROUP_ID',
                        '7'
                    )
                    
                    # Отзываем доступ
                    success = revoke_access_level_from_person(
                        hc_session,
                        person_id,
                        str(access_group_id),
                        access_type=1
                    )
                    
                    if success:
                        visit.access_revoked = True
                        visit.save(update_fields=['access_revoked'])
                        logger.info(
                            "Visit %s: Access revoked successfully after first exit",
                            visit.id
                        )
                    else:
                        logger.error(
                            "Visit %s: Failed to revoke access",
                            visit.id
                        )
                
            except Exception as e:
                logger.error(
                    "Visit %s: Error monitoring passages: %s",
                    visit.id, e
                )
                import traceback
                traceback.print_exc()
        
        # FIX #13: Обновляем gauge количества гостей в здании
        try:
            from .metrics import hikcentral_guests_inside
            guests_count = Visit.objects.filter(
                access_granted=True,
                access_revoked=False,
                first_entry_detected__isnull=False,
                first_exit_detected__isnull=True
            ).count()
            hikcentral_guests_inside.set(guests_count)
            logger.info("HikCentral: Guests inside building: %d", guests_count)
        except Exception as metric_exc:
            logger.warning("Failed to update guests_inside metric: %s", metric_exc)
        
        logger.info("HikCentral: monitor_guest_passages_task completed")
        
    except Exception as e:
        logger.error("HikCentral: monitor_guest_passages_task failed: %s", e)
        import traceback
        traceback.print_exc()


@shared_task(bind=True, queue='hikvision', max_retries=3, default_retry_delay=30)
def update_person_validity_task(self, visit_id: int) -> None:
    """
    FIX #8: Обновляет validity персоны в HikCentral при изменении времени визита.
    
    Логика:
    1. Получает Visit по visit_id
    2. Извлекает person_id из visit.hikcentral_person_id
    3. Обновляет endTime персоны через PUT /person/personUpdate
    4. Применяет изменения на устройства через reapplication API
    
    Retry mechanism:
    - max_retries=3 (до 3 попыток)
    - backoff: 30s → 60s → 120s
    """
    from django.conf import settings
    from datetime import datetime, time as dt_time
    
    try:
        from visitors.models import Visit
        visit = Visit.objects.select_related('guest').filter(
            id=visit_id
        ).first()
        
        if not visit:
            logger.warning("update_person_validity_task: Visit %s not found", visit_id)
            return
        
        # Проверяем, что доступ активен
        if not visit.access_granted or visit.access_revoked:
            logger.info(
                "update_person_validity_task: Visit %s has no active access, skipping",
                visit_id
            )
            return
        
        # Получаем person_id
        person_id = visit.hikcentral_person_id
        if not person_id and visit.guest:
            person_id = getattr(visit.guest, 'hikcentral_person_id', None)
        
        if not person_id:
            logger.warning(
                "update_person_validity_task: No person_id found for visit %s",
                visit_id
            )
            return
        
        # Получаем HikCentral server
        hc_server = _get_hikcentral_server()
        if not hc_server:
            raise RuntimeError('No HikCentral server available')
        
        # Формируем новое время окончания validity
        # Используем HIKCENTRAL_ACCESS_END_TIME из настроек
        access_end_time_str = getattr(
            settings,
            'HIKCENTRAL_ACCESS_END_TIME',
            '22:00'
        )
        access_end_time = datetime.strptime(access_end_time_str, '%H:%M').time()
        
        from django.utils import timezone
        now = timezone.now()
        end_datetime = timezone.make_aware(
            datetime.combine(now.date(), access_end_time)
        )
        
        # Формат времени для HikCentral API
        end_time_str = end_datetime.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        
        logger.info(
            "HikCentral: Updating person %s validity to %s (visit %s)",
            person_id, end_time_str, visit_id
        )
        
        # Используем context manager для автоматического закрытия сессии
        with HikCentralSession(hc_server) as hc_session:
            # Обновляем персону через PUT /person/personUpdate
            # Используем минимальный набор полей для обновления
            update_payload = {
                'personId': str(person_id),
                'endTime': end_time_str,
            }
            
            resp = hc_session.put(
                '/artemis/api/resource/v1/person/personUpdate',
                json=update_payload
            )
            
            if resp.status_code != 200:
                raise RuntimeError(
                    f'Failed to update person validity: {resp.status_code} - {resp.text}'
                )
            
            result = resp.json()
            if result.get('code') != '0':
                raise RuntimeError(
                    f'Failed to update person validity: code={result.get("code")}, '
                    f'msg={result.get("msg")}'
                )
            
            # Применяем изменения на устройства через reapplication API
            # Это важно, чтобы новое время validity применилось на турникетах
            reapp_resp = hc_session.post(
                '/artemis/api/visitor/v1/auth/reapplication'
            )
            
            if reapp_resp.status_code == 200:
                logger.info(
                    "HikCentral: Successfully applied validity update to devices "
                    "for person %s",
                    person_id
                )
            else:
                logger.warning(
                    "HikCentral: Reapplication returned %d for person %s",
                    reapp_resp.status_code, person_id
                )
        
        logger.info(
            "HikCentral: Successfully updated validity for person %s (visit %s)",
            person_id, visit_id
        )
        
    except Exception as exc:
        error_msg = f"Failed to update person validity: {exc}"
        logger.error("HikCentral: %s", error_msg)
        
        # Retry с exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 30 * (2 ** self.request.retries)
            logger.warning(
                "HikCentral: Retrying update_person_validity_task in %ds "
                "(attempt %d/%d)",
                countdown, self.request.retries + 1, self.max_retries
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                "HikCentral: Max retries reached for update_person_validity_task, "
                "visit_id=%s",
                visit_id
            )


@shared_task(bind=True, max_retries=3)
def send_security_alert_task(self, incident_id: int):
    """
    Celery task для отправки security alert по email.
    
    Args:
        incident_id: ID SecurityIncident
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Sending security alert for incident {incident_id}")
        
        from .utils import send_security_alert_sync
        send_security_alert_sync(incident_id)
        
        logger.info(f"Security alert sent successfully for incident {incident_id}")
        
    except Exception as exc:
        logger.error(f"Failed to send security alert for incident {incident_id}: {exc}")
        
        # Retry с exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            logger.warning(
                f"Retrying send_security_alert_task in {countdown}s "
                f"(attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(
                f"Max retries reached for send_security_alert_task, incident_id={incident_id}"
            )

