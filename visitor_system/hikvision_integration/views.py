from django.http import HttpRequest, JsonResponse, HttpResponseForbidden
from django.utils import timezone
from visitors.models import Visit
from visitors.models import STATUS_CHECKED_IN
from django.views.decorators.csrf import csrf_exempt
import hmac
import hashlib
import os


@csrf_exempt
def webhook_view(request: HttpRequest):
    secret = os.getenv('HIK_WEBHOOK_SECRET', '')
    if secret:
        signature = request.headers.get('X-Hikvision-Signature', '')
        body = request.body or b''
        digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, digest):
            return HttpResponseForbidden('Invalid signature')
    # Надежный парсинг JSON-тела
    import json
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        data = {}
    # Простая схема: ожидаем {"event":"face_pass","guest_id":123,"direction":"in"|"out","ts":"..."}
    if not data:
        return JsonResponse({'ok': True})
    evt = data or {}
    if evt.get('event') == 'face_pass' and evt.get('guest_id'):
        guest_id = int(evt['guest_id'])
        direction = evt.get('direction')
        if direction == 'in':
            v = Visit.objects.filter(guest_id=guest_id, status__in=['AWAITING_ARRIVAL', 'CREATED']).order_by('-created_at').first()
            if v:
                from visitors.views import check_in_visit
                try:
                    # дернуть уже существующую логику check-in по урлу сложно; здесь метим напрямую
                    v.entry_time = timezone.now()
                    v.status = STATUS_CHECKED_IN
                    v.save(update_fields=['entry_time', 'status'])
                except Exception:
                    pass
        elif direction == 'out':
            v = Visit.objects.filter(guest_id=guest_id, status=STATUS_CHECKED_IN).order_by('-entry_time').first()
            if v:
                try:
                    v.exit_time = timezone.now()
                    v.status = 'CHECKED_OUT'
                    v.save(update_fields=['exit_time', 'status'])
                except Exception:
                    pass
    return JsonResponse({'ok': True})

from django.shortcuts import render

# Create your views here.
