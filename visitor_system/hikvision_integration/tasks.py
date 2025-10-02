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
    upload_face_hikcentral_multipart,
    visitor_out,
    visitor_auth_reapplication,
)


logger = logging.getLogger(__name__)


def _get_device_session(device: HikDevice) -> HikSession:
    return HikSession(device)


def _get_hikcentral_session() -> HikCentralSession | None:
    server = HikCentralServer.objects.filter(enabled=True).first()
    return HikCentralSession(server) if server else None


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
        hc_session = _get_hikcentral_session()
        logger.info("Hik enroll: hc_session=%s", bool(hc_session))
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
            try:
                from visitors.models import GuestInvitation
                inv = None
                if task.visit_id:
                    inv = GuestInvitation.objects.filter(visit_id=task.visit_id).first()
                if not inv and (task.guest_id or payload.get('guest_id')):
                    gid = task.guest_id or payload.get('guest_id')
                    inv = GuestInvitation.objects.filter(
                        visit__guest_id=gid
                    ).first()
                photo_path = getattr(getattr(inv, 'guest_photo', None), 'path', None)
                if photo_path:
                    with open(photo_path, 'rb') as f:
                        image_bytes = f.read()
                        logger.info(
                            'Hik enroll: loaded invitation photo (%s bytes)',
                            len(image_bytes),
                        )
            except Exception:
                logger.exception('Hik enroll: failed to load invitation.guest_photo')

        logger.info(
            "Hik enroll: ensure_person start employee_no=%s name=%s",
            employee_no,
            name,
        )
        if hc_session:
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

        face_id = ''
        if image_bytes:
            logger.info("Hik enroll: upload_face start")
            
            # ГИБРИДНЫЙ ПОДХОД: Person через HCP, Face через ISAPI
            # Это обходит проблему с Face Group в HCP
            use_isapi_for_face = getattr(settings, 'HIKCENTRAL_USE_ISAPI_FOR_FACE', False)
            
            if use_isapi_for_face and hc_session:
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
                    
            elif hc_session:
                # HCP multipart upload (РЕКОМЕНДУЕМЫЙ метод)
                try:
                    logger.info("Hik enroll: Trying multipart upload for HCP")
                    face_id = upload_face_hikcentral_multipart(
                        hc_session,
                        face_lib_id,
                        image_bytes,
                        person_id,
                    )
                    logger.info("Hik enroll: Multipart upload result: %s", face_id)
                except Exception as e:
                    logger.error("Hik enroll: HCP multipart upload failed: %s", e)
                    # Fallback уже встроен в upload_face_hikcentral_multipart
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
        if hc_session:
            # Через Visitor API триггерим применение
            try:
                visitor_auth_reapplication(hc_session, person_id)
            except Exception:
                logger.exception("Hik enroll: reapplication failed, continue")
        else:
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
        hc_session = _get_hikcentral_session()
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
        if hc_session:
            # Через Visitor API отметим выход
            try:
                visitor_out(hc_session, {'personId': str(person_id)})
            except Exception:
                logger.exception("Hik revoke: visitor_out failed, continue")
        else:
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


@shared_task(queue='hikvision')
def assign_access_level_task(task_id: int) -> None:
    """
    Назначает гостю access level group после успешной загрузки фото.
    
    Логика:
    1. Получает person_id из task.payload или guest.hikcentral_person_id
    2. Назначает access level group (из settings.HIKCENTRAL_GUEST_ACCESS_GROUP_ID)
    3. Применяет настройки на устройства через reapplication API
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
        hc_session = _get_hikcentral_session()
        if not hc_session:
            raise RuntimeError('No HikCentral session available')
        
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
                if visit and visit.guest and hasattr(visit.guest, 'hikcentral_person_id'):
                    person_id = visit.guest.hikcentral_person_id
            except Exception as e:
                logger.warning("Failed to get person_id from Visit: %s", e)
        
        if not person_id:
            raise RuntimeError(
                f'person_id not found for task {task_id}, '
                f'guest_id={task.guest_id}, visit_id={task.visit_id}'
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
        
    except Exception as e:
        error_msg = f"Failed to assign access level: {e}"
        logger.error("HikCentral: %s", error_msg)
        task.status = 'failed'
        task.last_error = error_msg
        task.save(update_fields=['status', 'last_error'])
        import traceback
        traceback.print_exc()


@shared_task(queue='hikvision')
def monitor_guest_passages_task() -> None:
    """
    Периодическая задача для мониторинга проходов гостей через турникеты.
    
    Логика (Вариант В):
    1. Находит все активные визиты с access_granted=True и access_revoked=False
    2. Для каждого визита запрашивает события проходов за последние 10 минут
    3. Обновляет счётчики входов/выходов
    4. После ПЕРВОГО ВЫХОДА:
       - Отзывает доступ через revoke_access_level_from_person()
       - Помечает access_revoked=True
    
    Запускается каждые 5-10 минут через Celery Beat.
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
        
        hc_session = _get_hikcentral_session()
        if not hc_session:
            logger.error("HikCentral: No session available for monitoring")
            return
        
        # Временной диапазон: последние 10 минут
        now = timezone.now()
        start_time = now - timedelta(minutes=10)
        
        for visit in active_visits:
            try:
                if not visit.hikcentral_person_id:
                    logger.warning(
                        "Visit %s: No hikcentral_person_id",
                        visit.id
                    )
                    continue
                
                person_id = str(visit.hikcentral_person_id)
                
                # Получаем события проходов
                # event_type: 1 - вход, 2 - выход (согласно документации)
                events_data = get_door_events(
                    hc_session,
                    person_id=person_id,
                    person_name=None,  # Можно использовать имя для фильтрации
                    start_time=start_time.isoformat(),
                    end_time=now.isoformat(),
                    door_index_codes=None,  # None = все двери
                    event_type=None,  # None = все типы событий
                    page_no=1,
                    page_size=100
                )
                
                if not events_data or 'list' not in events_data:
                    continue
                
                events = events_data.get('list', [])
                if not events:
                    continue
                
                logger.info(
                    "Visit %s: Found %d door events in last 10 minutes",
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
                    elif event_type == 2:  # Выход
                        new_exits += 1
                        if not first_exit_time or event_time < first_exit_time:
                            first_exit_time = event_time
                
                # Обновляем счётчики
                if new_entries > 0 or new_exits > 0:
                    visit.entry_count += new_entries
                    visit.exit_count += new_exits
                    
                    if first_entry_time and not visit.first_entry_detected:
                        visit.first_entry_detected = first_entry_time
                        logger.info(
                            "Visit %s: First ENTRY detected at %s",
                            visit.id, first_entry_time
                        )
                    
                    if first_exit_time and not visit.first_exit_detected:
                        visit.first_exit_detected = first_exit_time
                        logger.info(
                            "Visit %s: First EXIT detected at %s",
                            visit.id, first_exit_time
                        )
                    
                    visit.save(update_fields=[
                        'entry_count', 'exit_count',
                        'first_entry_detected', 'first_exit_detected'
                    ])
                    
                    logger.info(
                        "Visit %s: Updated counts - entries=%d, exits=%d",
                        visit.id, visit.entry_count, visit.exit_count
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
        
        logger.info("HikCentral: monitor_guest_passages_task completed")
        
    except Exception as e:
        logger.error("HikCentral: monitor_guest_passages_task failed: %s", e)
        import traceback
        traceback.print_exc()


