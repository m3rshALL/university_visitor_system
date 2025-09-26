from celery import shared_task
from django.utils import timezone
from .models import HikAccessTask, HikDevice, HikPersonBinding
from .services import HikSession, ensure_person, upload_face, assign_access, revoke_access


def _get_session(device: HikDevice) -> HikSession:
    return HikSession(device.host, device.port, device.username, device.password, device.verify_ssl)


@shared_task(queue='hikvision')
def enroll_face_task(task_id: int) -> None:
    task = HikAccessTask.objects.filter(id=task_id).first()
    if not task:
        return
    task.status = 'running'
    task.attempts += 1
    task.save(update_fields=['status', 'attempts'])
    try:
        device = task.device or HikDevice.objects.filter(enabled=True, is_primary=True).first()
        if not device:
            raise RuntimeError('No active HikDevice configured')
        session = _get_session(device)
        payload = task.payload or {}
        employee_no = str(payload.get('employee_no') or payload.get('guest_id') or task.guest_id)
        name = payload.get('name') or 'Guest'
        # Период доступа по умолчанию: сейчас до +1 день
        valid_from = payload.get('valid_from') or timezone.now().isoformat()
        valid_to = payload.get('valid_to') or (timezone.now() + timezone.timedelta(days=1)).isoformat()
        face_lib_id = payload.get('face_lib_id') or '1'
        image_bytes = payload.get('image_bytes')  # ожидается bytes в реальной реализации
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('utf-8')

        person_id = ensure_person(session, employee_no, name, valid_from, valid_to)
        face_id = ''
        if image_bytes:
            face_id = upload_face(session, face_lib_id, image_bytes, person_id)
        # Двери по умолчанию — из конфигурации устройства
        door_ids = payload.get('door_ids') or (device.doors_json if isinstance(device.doors_json, list) else [])
        assign_access(session, person_id, door_ids, valid_from, valid_to)
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
        task.status = 'success'
        task.last_error = ''
        task.save(update_fields=['status', 'last_error'])
    except Exception as e:
        task.status = 'failed'
        task.last_error = str(e)
        task.save(update_fields=['status', 'last_error'])


@shared_task(queue='hikvision')
def revoke_access_task(task_id: int) -> None:
    task = HikAccessTask.objects.filter(id=task_id).first()
    if not task:
        return
    task.status = 'running'
    task.attempts += 1
    task.save(update_fields=['status', 'attempts'])
    try:
        device = task.device or HikDevice.objects.filter(enabled=True, is_primary=True).first()
        if not device:
            raise RuntimeError('No active HikDevice configured')
        session = _get_session(device)
        payload = task.payload or {}
        person_id = payload.get('person_id') or ''
        if not person_id:
            binding = HikPersonBinding.objects.filter(guest_id=task.guest_id, device=device).first()
            if binding:
                person_id = binding.person_id
        if not person_id:
            raise RuntimeError('person_id not found for revoke')
        door_ids = payload.get('door_ids') or (device.doors_json if isinstance(device.doors_json, list) else [])
        revoke_access(session, person_id, door_ids)
        HikPersonBinding.objects.filter(guest_id=task.guest_id, device=device).update(status='revoked')
        task.status = 'success'
        task.last_error = ''
        task.save(update_fields=['status', 'last_error'])
    except Exception as e:
        task.status = 'failed'
        task.last_error = str(e)
        task.save(update_fields=['status', 'last_error'])


