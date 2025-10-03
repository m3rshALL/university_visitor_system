# 🎯 ПЛАН ДОРАБОТКИ СИСТЕМЫ

**Дата анализа:** 2025-01-03  
**Статус:** 9/26 функций реализовано (35%)

---

## 📊 EXECUTIVE SUMMARY

### Текущее состояние

**✅ КРИТИЧЕСКИЕ (5/5 = 100%)**
- person_id сохранение
- Race condition (chain)
- Retry mechanism
- auto_close + revoke
- Cleanup при отмене

**⚠️ ВЫСОКИЙ ПРИОРИТЕТ (3/6 = 50%)**
- ✅ Обработка изменения времени
- ✅ Обработка отмены CANCELLED
- ✅ Prometheus metrics
- ❌ StudentVisit support
- ❌ Уведомления о проходах
- ❌ Проверка validity person
- ❌ Rate limiting

**❌ СРЕДНИЙ ПРИОРИТЕТ (1/6 = 17%)**
- ✅ Prometheus metrics
- ❌ Security dashboard
- ❌ Manual control UI
- ❌ DoorEvent model
- ❌ Failed recognition handling

**❌ НИЗКИЙ ПРИОРИТЕТ (0/9 = 0%)**
- Все 9 функций не реализованы

---

## 🚨 ПРИОРИТЕТ 1: ВЫСОКИЙ (Must Have)

### 1. StudentVisit HikCentral Support

**Проблема:**
```python
# StudentVisit не имеет полей для интеграции
class StudentVisit(models.Model):
    # ❌ Нет: access_granted, hikcentral_person_id, first_entry_detected
```

**Решение:**

```python
# visitors/models.py
class StudentVisit(models.Model):
    # ... existing fields ...
    
    # HikCentral integration fields
    access_granted = models.BooleanField(default=False, verbose_name="Доступ выдан")
    access_revoked = models.BooleanField(default=False, verbose_name="Доступ отозван")
    hikcentral_person_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="HikCentral Person ID")
    
    # Passage tracking
    first_entry_detected = models.DateTimeField(blank=True, null=True, verbose_name="Первый вход (автоматически)")
    first_exit_detected = models.DateTimeField(blank=True, null=True, verbose_name="Первый выход (автоматически)")
    entry_count = models.IntegerField(default=0, verbose_name="Счётчик входов")
    exit_count = models.IntegerField(default=0, verbose_name="Счётчик выходов")
    
    class Meta:
        # ... existing meta ...
        indexes = [
            # ... existing indexes ...
            Index(fields=['access_granted', 'access_revoked'], name='student_visit_access_idx'),
            Index(fields=['hikcentral_person_id'], name='student_visit_hik_person_idx'),
        ]
```

**Обновить задачи:**

```python
# hikvision_integration/tasks.py

# В monitor_guest_passages_task добавить:
from visitors.models import StudentVisit

def monitor_guest_passages_task():
    # Обрабатываем Visit
    visits = Visit.objects.filter(access_granted=True, status='CHECKED_IN', access_revoked=False)
    _process_passages(visits, 'Visit')
    
    # Обрабатываем StudentVisit
    student_visits = StudentVisit.objects.filter(access_granted=True, status='CHECKED_IN', access_revoked=False)
    _process_passages(student_visits, 'StudentVisit')

def _process_passages(visits_qs, model_name):
    """Универсальная обработка проходов для Visit и StudentVisit"""
    for visit in visits_qs:
        if not visit.hikcentral_person_id:
            continue
        
        # Получаем события из HCP
        events = get_door_events(visit.hikcentral_person_id)
        
        for event in events:
            if event['eventType'] == 1:  # Entry
                visit.entry_count += 1
                if not visit.first_entry_detected:
                    visit.first_entry_detected = parse(event['eventTime'])
                    logger.info("%s %s: First entry detected", model_name, visit.id)
            elif event['eventType'] == 2:  # Exit
                visit.exit_count += 1
                if not visit.first_exit_detected:
                    visit.first_exit_detected = parse(event['eventTime'])
                    # Автоматическая блокировка при выходе
                    revoke_access_level_task.apply_async(args=[visit.id], countdown=30)
                    logger.info("%s %s: First exit detected, revoking access", model_name, visit.id)
        
        visit.save(update_fields=['entry_count', 'exit_count', 'first_entry_detected', 'first_exit_detected'])
```

**Миграция:**
```bash
python manage.py makemigrations visitors
python manage.py migrate
```

**Оценка:** 4 часа

---

### 2. Уведомления о проходах гостей

**Проблема:** Сотрудник не знает когда гость прошёл турникет

**Решение:**

```python
# visitors/models.py

class Visit(models.Model):
    # ... existing fields ...
    
    # Notification flags
    entry_notification_sent = models.BooleanField(default=False, verbose_name="Уведомление о входе отправлено")
    exit_notification_sent = models.BooleanField(default=False, verbose_name="Уведомление о выходе отправлено")

class StudentVisit(models.Model):
    # ... existing fields ...
    
    entry_notification_sent = models.BooleanField(default=False)
    exit_notification_sent = models.BooleanField(default=False)
```

```python
# hikvision_integration/tasks.py

def _process_passages(visits_qs, model_name):
    for visit in visits_qs:
        # ... existing event processing ...
        
        # Отправляем уведомления
        if visit.first_entry_detected and not visit.entry_notification_sent:
            _send_entry_notification(visit, model_name)
            visit.entry_notification_sent = True
        
        if visit.first_exit_detected and not visit.exit_notification_sent:
            _send_exit_notification(visit, model_name)
            visit.exit_notification_sent = True
        
        visit.save(update_fields=['entry_notification_sent', 'exit_notification_sent'])

def _send_entry_notification(visit, model_name):
    """Отправка уведомления о входе гостя"""
    from notifications.tasks import send_notification_task
    
    employee = visit.employee if model_name == 'Visit' else visit.registered_by
    guest_name = visit.guest.full_name
    time_str = visit.first_entry_detected.strftime('%H:%M')
    
    send_notification_task.apply_async(args=[
        employee.id,
        '🚪 Гость вошёл в здание',
        f'{guest_name} прошёл турникет в {time_str}',
        'info'
    ])

def _send_exit_notification(visit, model_name):
    """Отправка уведомления о выходе гостя"""
    from notifications.tasks import send_notification_task
    
    employee = visit.employee if model_name == 'Visit' else visit.registered_by
    guest_name = visit.guest.full_name
    time_str = visit.first_exit_detected.strftime('%H:%M')
    
    send_notification_task.apply_async(args=[
        employee.id,
        '👋 Гость покинул здание',
        f'{guest_name} вышел из здания в {time_str}',
        'success'
    ])
```

**Оценка:** 2 часа

---

### 3. Проверка validity person перед назначением access

**Проблема:** Нет проверки что person существует и валиден

**Решение:**

```python
# hikvision_integration/tasks.py

@shared_task(bind=True, queue='hikvision', max_retries=5, default_retry_delay=60)
def assign_access_level_task(self, task_id):
    # ... existing code до получения person_id ...
    
    # FIX #10: Проверяем validity person перед назначением
    try:
        person_info = get_person_hikcentral(session, person_id)
        
        if not person_info:
            logger.error("HikCentral: Person %s not found, cannot assign access", person_id)
            raise RuntimeError(f'Person {person_id} not found in HikCentral')
        
        # Проверяем срок действия
        valid_to = person_info.get('endTime')
        if valid_to:
            valid_to_dt = parse(valid_to)
            if valid_to_dt < timezone.now():
                logger.error("HikCentral: Person %s expired (validTo=%s)", person_id, valid_to)
                raise RuntimeError(f'Person {person_id} expired')
        
        # Проверяем статус (если есть)
        person_status = person_info.get('status')
        if person_status is not None and person_status != 1:
            logger.error("HikCentral: Person %s is not active (status=%s)", person_id, person_status)
            raise RuntimeError(f'Person {person_id} is not active')
        
        logger.info(
            "HikCentral: Person %s validation passed (status=%s, validTo=%s)",
            person_id, person_status, valid_to
        )
        
    except Exception as exc:
        logger.error("HikCentral: Person validation failed: %s", exc)
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        raise
    
    # ... existing code для назначения access ...
```

**Оценка:** 1 час

---

### 4. Rate limiting для HikCentral API

**Проблема:** Массовая регистрация → 429 Too Many Requests

**Решение 1: Celery rate_limit**

```python
# hikvision_integration/tasks.py

@shared_task(
    bind=True,
    queue='hikvision',
    max_retries=3,
    default_retry_delay=30,
    rate_limit='10/m'  # 10 задач в минуту
)
def enroll_face_task(self, task_id):
    # ... existing code ...
```

**Решение 2: Отдельная очередь с concurrency=1**

```python
# visitor_system/celery.py

app.conf.task_routes = {
    'hikvision_integration.tasks.enroll_face_task': {
        'queue': 'hikvision_serial',  # Последовательная обработка
    },
    'hikvision_integration.tasks.assign_access_level_task': {
        'queue': 'hikvision_serial',
    },
    'hikvision_integration.tasks.revoke_access_level_task': {
        'queue': 'hikvision_serial',
    },
}
```

**Запуск worker:**
```bash
# Обычный worker для фоновых задач
celery -A visitor_system worker -Q hikvision --pool=solo -c 4

# Последовательный worker для критичных задач
celery -A visitor_system worker -Q hikvision_serial --pool=solo -c 1
```

**Оценка:** 1 час

---

## 📊 ПРИОРИТЕТ 2: СРЕДНИЙ (Should Have)

### 5. Security Real-time Dashboard

**Что нужно:**
- Список гостей в здании (live)
- Последние 10 проходов
- Alerts: гости без выхода >2 часа
- Статистика по департаментам

**Решение:**

```python
# realtime_dashboard/consumers.py

class SecurityDashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Запускаем периодическую отправку данных
        asyncio.create_task(self.send_updates())
    
    async def send_updates(self):
        while True:
            # Гости в здании
            guests_inside = await database_sync_to_async(
                Visit.objects.filter(
                    status='CHECKED_IN',
                    access_granted=True,
                    access_revoked=False
                ).count
            )()
            
            # Последние проходы (нужна модель DoorEvent)
            recent_passages = []  # TODO: implement after DoorEvent model
            
            # Гости без выхода >2 часа
            cutoff = timezone.now() - timedelta(hours=2)
            overdue_guests = await database_sync_to_async(
                list
            )(Visit.objects.filter(
                status='CHECKED_IN',
                first_entry_detected__lt=cutoff,
                first_exit_detected__isnull=True
            ).select_related('guest'))
            
            await self.send(text_data=json.dumps({
                'guests_inside': guests_inside,
                'recent_passages': recent_passages,
                'overdue_guests': [
                    {
                        'id': v.id,
                        'name': v.guest.full_name,
                        'entry_time': v.first_entry_detected.isoformat(),
                        'duration_hours': (timezone.now() - v.first_entry_detected).total_seconds() / 3600
                    }
                    for v in overdue_guests
                ]
            }))
            
            await asyncio.sleep(5)  # Обновляем каждые 5 секунд
```

**Шаблон:**
```html
<!-- templates/realtime_dashboard/security.html -->
<div class="dashboard">
    <div class="stat-card">
        <h3>Гостей в здании</h3>
        <span id="guests-inside">0</span>
    </div>
    
    <div class="alerts">
        <h3>⚠️ Гости без выхода >2 часов</h3>
        <ul id="overdue-guests"></ul>
    </div>
    
    <div class="recent-passages">
        <h3>Последние проходы</h3>
        <ul id="passages"></ul>
    </div>
</div>

<script>
const ws = new WebSocket('ws://localhost:8000/ws/security/');
ws.onmessage = function(e) {
    const data = JSON.parse(e.data);
    document.getElementById('guests-inside').textContent = data.guests_inside;
    
    // Отображаем просроченных гостей
    const overdueList = document.getElementById('overdue-guests');
    overdueList.innerHTML = data.overdue_guests.map(g => 
        `<li class="alert">${g.name} (в здании ${g.duration_hours.toFixed(1)}ч)</li>`
    ).join('');
};
</script>
```

**Оценка:** 6 часов

---

### 6. Manual Control UI (кнопки управления доступом)

**Решение:**

```python
# visitors/views.py

@require_POST
@login_required
def manual_revoke_access(request, visit_id):
    """Ручная блокировка доступа для визита"""
    visit = get_object_or_404(Visit, id=visit_id)
    
    # Проверка прав: только Reception или сотрудник-владелец
    if not (request.user.groups.filter(name='Reception').exists() or visit.employee == request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if visit.access_granted and not visit.access_revoked:
        try:
            from hikvision_integration.tasks import revoke_access_level_task
            revoke_access_level_task.apply_async(args=[visit.id], countdown=2)
            
            messages.success(request, '✅ Доступ будет заблокирован в течение минуты')
            logger.info("Manual revoke scheduled for visit %s by user %s", visit.id, request.user.username)
        except Exception as exc:
            messages.error(request, f'❌ Ошибка: {exc}')
            logger.error("Failed to schedule manual revoke: %s", exc)
    else:
        messages.warning(request, 'Доступ уже заблокирован или не выдавался')
    
    return redirect('visit_detail', pk=visit_id)


@require_POST
@login_required
def manual_extend_access(request, visit_id):
    """Продление доступа (обновление validity)"""
    visit = get_object_or_404(Visit, id=visit_id)
    
    if not (request.user.groups.filter(name='Reception').exists() or visit.employee == request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Продлеваем на 2 часа
    new_exit_time = timezone.now() + timedelta(hours=2)
    visit.expected_exit_time = new_exit_time
    visit.save(update_fields=['expected_exit_time'])
    
    # Signal update_hikcentral_validity_on_time_change автоматически обновит HCP
    
    messages.success(request, f'✅ Доступ продлён до {new_exit_time.strftime("%H:%M")}')
    return redirect('visit_detail', pk=visit_id)
```

**Шаблон:**
```html
<!-- templates/visitors/visit_detail.html -->

{% if visit.access_granted and not visit.access_revoked %}
<div class="access-controls">
    <form method="post" action="{% url 'manual_revoke_access' visit.id %}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="btn btn-danger" onclick="return confirm('Заблокировать доступ?')">
            🚫 Заблокировать доступ
        </button>
    </form>
    
    <form method="post" action="{% url 'manual_extend_access' visit.id %}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="btn btn-warning">
            ⏰ Продлить на 2 часа
        </button>
    </form>
</div>
{% elif not visit.access_granted %}
<div class="alert alert-warning">
    ⏳ Доступ ещё не выдан (задача в очереди)
</div>
{% else %}
<div class="alert alert-secondary">
    🔒 Доступ заблокирован
</div>
{% endif %}

<!-- История проходов -->
{% if visit.first_entry_detected or visit.first_exit_detected %}
<div class="passage-history">
    <h4>История проходов</h4>
    <ul>
        {% if visit.first_entry_detected %}
        <li>
            🚪 Вход: {{ visit.first_entry_detected|date:"d.m.Y H:i" }}
            (всего входов: {{ visit.entry_count }})
        </li>
        {% endif %}
        {% if visit.first_exit_detected %}
        <li>
            👋 Выход: {{ visit.first_exit_detected|date:"d.m.Y H:i" }}
            (всего выходов: {{ visit.exit_count }})
        </li>
        {% endif %}
    </ul>
</div>
{% endif %}
```

**URLs:**
```python
# visitors/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('visit/<int:visit_id>/revoke-access/', views.manual_revoke_access, name='manual_revoke_access'),
    path('visit/<int:visit_id>/extend-access/', views.manual_extend_access, name='manual_extend_access'),
]
```

**Оценка:** 3 часа

---

### 7. DoorEvent Model (фотофиксация проходов)

**Решение:**

```python
# hikvision_integration/models.py

class DoorEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        (1, 'Entry'),
        (2, 'Exit'),
        (-1, 'Failed'),
    ]
    
    visit = models.ForeignKey(
        'visitors.Visit',
        on_delete=models.CASCADE,
        related_name='door_events',
        null=True,  # Может быть null для StudentVisit
        blank=True
    )
    student_visit = models.ForeignKey(
        'visitors.StudentVisit',
        on_delete=models.CASCADE,
        related_name='door_events',
        null=True,
        blank=True
    )
    
    event_type = models.IntegerField(choices=EVENT_TYPE_CHOICES, verbose_name="Тип события")
    event_time = models.DateTimeField(verbose_name="Время события")
    door_name = models.CharField(max_length=100, verbose_name="Название двери")
    event_pic_url = models.URLField(blank=True, null=True, verbose_name="URL фото с камеры")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-event_time']
        verbose_name = "Событие прохода"
        verbose_name_plural = "События проходов"
        indexes = [
            models.Index(fields=['visit', '-event_time']),
            models.Index(fields=['student_visit', '-event_time']),
            models.Index(fields=['event_type', '-event_time']),
        ]
    
    def __str__(self):
        event_name = dict(self.EVENT_TYPE_CHOICES).get(self.event_type, 'Unknown')
        return f"{event_name} at {self.door_name} ({self.event_time.strftime('%Y-%m-%d %H:%M')})"
```

**Обновить monitor_guest_passages_task:**

```python
# hikvision_integration/tasks.py

def _process_passages(visits_qs, model_name):
    for visit in visits_qs:
        # ... existing code ...
        
        # Сохраняем события в DoorEvent
        for event in events:
            # Проверяем, уже записано ли это событие
            event_time = parse(event.get('eventTime'))
            event_type = event.get('eventType')
            
            existing = DoorEvent.objects.filter(
                **{model_name.lower(): visit},  # visit= или student_visit=
                event_time=event_time,
                event_type=event_type
            ).exists()
            
            if not existing:
                DoorEvent.objects.create(
                    **{model_name.lower(): visit},
                    event_type=event_type,
                    event_time=event_time,
                    door_name=event.get('doorName', 'Unknown'),
                    event_pic_url=event.get('eventPicUrl')  # Сохраняем фото!
                )
```

**Миграция:**
```bash
python manage.py makemigrations hikvision_integration
python manage.py migrate
```

**Оценка:** 3 часа

---

## 🔧 ПРИОРИТЕТ 3: НИЗКИЙ (Nice to Have)

### 8. Cleanup Old Persons Task

**Решение:**

```python
# hikvision_integration/tasks.py

@shared_task(bind=True, queue='hikvision', max_retries=3)
def cleanup_old_persons_task(self):
    """
    Удаляет персоны из HikCentral с validTo < now() - 30 days.
    Запускается раз в месяц через beat.
    """
    from datetime import timedelta
    from hikvision_integration.services import HikCentralSession, delete_person_hikcentral
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Находим старые визиты
    old_visits = Visit.objects.filter(
        hikcentral_person_id__isnull=False,
        entry_time__lt=cutoff_date,
        status__in=['CHECKED_OUT', 'CANCELLED']
    )
    
    session = HikCentralSession(...)
    deleted_count = 0
    errors = []
    
    for visit in old_visits:
        try:
            # Удаляем person из HCP
            success = delete_person_hikcentral(session, visit.hikcentral_person_id)
            if success:
                visit.hikcentral_person_id = None
                visit.save(update_fields=['hikcentral_person_id'])
                deleted_count += 1
            else:
                errors.append(f"Visit {visit.id}: deletion returned False")
        except Exception as exc:
            errors.append(f"Visit {visit.id}: {exc}")
            logger.error("Failed to delete person %s: %s", visit.hikcentral_person_id, exc)
    
    logger.info("Cleanup completed: %d persons deleted, %d errors", deleted_count, len(errors))
    return {'deleted': deleted_count, 'errors': errors}
```

```python
# hikvision_integration/services.py

def delete_person_hikcentral(session: HikCentralSession, person_id: str) -> bool:
    """Удаляет person из HikCentral"""
    try:
        resp = session.delete(f'/artemis/api/resource/v1/person/single/delete', json={
            'personId': str(person_id)
        })
        
        result = resp.json()
        if result.get('code') == '0':
            logger.info("HikCentral: Person %s deleted successfully", person_id)
            return True
        else:
            logger.warning("HikCentral: Failed to delete person %s: %s", person_id, result.get('msg'))
            return False
    except Exception as exc:
        logger.error("HikCentral: Error deleting person %s: %s", person_id, exc)
        return False
```

**Beat schedule:**
```python
# visitor_system/celery.py

app.conf.beat_schedule = {
    # ... existing schedules ...
    'cleanup-old-persons': {
        'task': 'hikvision_integration.tasks.cleanup_old_persons_task',
        'schedule': crontab(hour=3, minute=0, day_of_month='1'),  # 1-го числа месяца в 3:00
    },
}
```

**Оценка:** 2 часа

---

### 9. Защита от дубликатов person

**Решение:**

```python
# visitors/models.py

class Guest(models.Model):
    # ... existing fields ...
    
    # Постоянный person_id для переиспользования
    permanent_hikcentral_person_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Постоянный HikCentral Person ID"
    )
```

```python
# hikvision_integration/tasks.py

def enroll_face_task(task_id):
    # ... existing code ...
    
    # Проверяем, есть ли у Guest постоянный person_id
    guest = task.guest
    if guest.permanent_hikcentral_person_id:
        logger.info(
            "Guest %s has permanent person_id %s, reusing",
            guest.id, guest.permanent_hikcentral_person_id
        )
        person_id = guest.permanent_hikcentral_person_id
        
        # Обновляем фото для существующего person
        upload_face_hikcentral(session, person_id, photo_data)
    else:
        # Создаём нового person
        person_id = ensure_person_hikcentral(...)
        
        # Сохраняем person_id как постоянный
        guest.permanent_hikcentral_person_id = str(person_id)
        guest.save(update_fields=['permanent_hikcentral_person_id'])
        logger.info("Guest %s assigned permanent person_id %s", guest.id, person_id)
    
    # ... rest of the code ...
```

**Миграция:**
```bash
python manage.py makemigrations visitors
python manage.py migrate
```

**Оценка:** 2 часа

---

### 10. Webhook от HikCentral (вместо polling)

**Решение:**

```python
# visitors/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('api/hikvision/webhook/', views.hikvision_webhook, name='hikvision_webhook'),
]
```

```python
# visitors/views.py

@csrf_exempt
@require_POST
def hikvision_webhook(request):
    """
    Endpoint для приёма webhook от HikCentral.
    Обрабатывает события проходов в реальном времени.
    """
    try:
        payload = json.loads(request.body)
        
        event_type = payload.get('eventType')
        person_id = payload.get('personId')
        event_time_str = payload.get('eventTime')
        door_name = payload.get('doorName', 'Unknown')
        event_pic_url = payload.get('eventPicUrl')
        
        logger.info("HikCentral webhook: eventType=%s, personId=%s", event_type, person_id)
        
        # Находим визит по person_id
        visit = Visit.objects.filter(hikcentral_person_id=person_id).first()
        if not visit:
            # Может быть StudentVisit
            student_visit = StudentVisit.objects.filter(hikcentral_person_id=person_id).first()
            if not student_visit:
                logger.warning("No visit found for person_id %s", person_id)
                return JsonResponse({'status': 'ok', 'message': 'No visit found'})
            visit = student_visit
            model_name = 'StudentVisit'
        else:
            model_name = 'Visit'
        
        event_time = parse(event_time_str)
        
        # Обрабатываем событие
        if event_type == 1:  # Entry
            visit.entry_count += 1
            if not visit.first_entry_detected:
                visit.first_entry_detected = event_time
                # Отправляем уведомление
                _send_entry_notification(visit, model_name)
        elif event_type == 2:  # Exit
            visit.exit_count += 1
            if not visit.first_exit_detected:
                visit.first_exit_detected = event_time
                # Блокируем доступ
                revoke_access_level_task.apply_async(args=[visit.id], countdown=30)
                # Отправляем уведомление
                _send_exit_notification(visit, model_name)
        
        visit.save(update_fields=['entry_count', 'exit_count', 'first_entry_detected', 'first_exit_detected'])
        
        # Сохраняем событие
        DoorEvent.objects.create(
            **{model_name.lower(): visit},
            event_type=event_type,
            event_time=event_time,
            door_name=door_name,
            event_pic_url=event_pic_url
        )
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as exc:
        logger.error("HikCentral webhook error: %s", exc, exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)
```

**Настройка в HikCentral:**
1. Event Subscription → Door Events
2. Callback URL: `https://yourdomain.com/api/hikvision/webhook/`
3. Event Types: Entry (1), Exit (2)

**Оценка:** 3 часа

---

## 🧪 ДОПОЛНИТЕЛЬНО: Улучшение качества кода

### 11. Unit Tests

**Проблема:** Нет unit тестов, только интеграционные скрипты

**Решение:**

```python
# hikvision_integration/tests.py

from django.test import TestCase
from unittest.mock import Mock, patch
from hikvision_integration.tasks import assign_access_level_task
from hikvision_integration.models import HikAccessTask
from visitors.models import Visit, Guest

class AssignAccessTaskTestCase(TestCase):
    def setUp(self):
        self.guest = Guest.objects.create(
            full_name="Test Guest",
            phone_number="+77001234567"
        )
        self.visit = Visit.objects.create(
            guest=self.guest,
            status='CHECKED_IN',
            hikcentral_person_id='12345'
        )
        self.task = HikAccessTask.objects.create(
            kind='assign_access',
            visit_id=self.visit.id,
            guest_id=self.guest.id,
            payload={'guest_id': self.guest.id}
        )
    
    @patch('hikvision_integration.tasks.HikCentralSession')
    @patch('hikvision_integration.tasks.get_person_hikcentral')
    @patch('hikvision_integration.tasks.assign_access_level_to_person')
    def test_assign_access_success(self, mock_assign, mock_get_person, mock_session):
        # Mock person info
        mock_get_person.return_value = {
            'personId': '12345',
            'status': 1,
            'endTime': '2025-12-31T23:59:59+00:00'
        }
        
        # Mock assign success
        mock_assign.return_value = True
        
        # Run task
        assign_access_level_task(self.task.id)
        
        # Assert
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'success')
        
        self.visit.refresh_from_db()
        self.assertTrue(self.visit.access_granted)
    
    @patch('hikvision_integration.tasks.HikCentralSession')
    @patch('hikvision_integration.tasks.get_person_hikcentral')
    def test_assign_access_person_not_found(self, mock_get_person, mock_session):
        # Person not found
        mock_get_person.return_value = None
        
        # Run task (should raise)
        with self.assertRaises(RuntimeError) as context:
            assign_access_level_task(self.task.id)
        
        self.assertIn('not found', str(context.exception))
```

**Запуск тестов:**
```bash
python manage.py test hikvision_integration
```

**Оценка:** 8 часов (покрытие основных сценариев)

---

### 12. Resolve TODO Comments

**Найдено 2 TODO:**

1. `visitors/views.py:711`
```python
# TODO: Проверка прав доступа, если нужна
```

**Решение:**
```python
# visitors/views.py line 711
def cancel_visit_view(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    
    # Проверка прав: Reception или владелец визита
    if not (request.user.groups.filter(name='Reception').exists() or visit.employee == request.user):
        messages.error(request, 'У вас нет прав для отмены этого визита')
        return redirect('visit_detail', pk=pk)
    
    # ... rest of the code ...
```

2. `visitors/signals.py:113`
```python
# TODO (Продвинутый уровень): Попытка заполнить из данных allauth.
```

**Решение:**
```python
# visitors/signals.py line 113
@receiver(post_save, sender=UserModel)
def create_employee_profile_from_allauth(instance, created, **kwargs):
    if created:
        try:
            # Пытаемся получить данные из allauth (Microsoft)
            from allauth.socialaccount.models import SocialAccount
            
            social = SocialAccount.objects.filter(user=instance).first()
            if social and social.provider == 'microsoft':
                extra_data = social.extra_data
                
                EmployeeProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'department_name': extra_data.get('department', ''),
                        'job_title': extra_data.get('jobTitle', ''),
                        'mobile_phone': extra_data.get('mobilePhone', ''),
                        'office_location': extra_data.get('officeLocation', ''),
                    }
                )
                logger.info("Created EmployeeProfile for %s from Microsoft data", instance.username)
        except Exception as exc:
            logger.warning("Failed to create profile from allauth: %s", exc)
```

**Оценка:** 1 час

---

## 📈 ROADMAP

### Sprint 1 (Неделя 1) - ВЫСОКИЙ ПРИОРИТЕТ
- [x] ~~Критические (5/5)~~ - УЖЕ СДЕЛАНО ✅
- [ ] **1. StudentVisit support** - 4ч
- [ ] **2. Уведомления о проходах** - 2ч
- [ ] **3. Проверка validity person** - 1ч
- [ ] **4. Rate limiting** - 1ч

**Итого Sprint 1:** 8 часов = 1 рабочий день

### Sprint 2 (Неделя 2) - СРЕДНИЙ ПРИОРИТЕТ
- [ ] **5. Security dashboard** - 6ч
- [ ] **6. Manual control UI** - 3ч
- [ ] **7. DoorEvent model** - 3ч

**Итого Sprint 2:** 12 часов = 1.5 рабочих дня

### Sprint 3 (Неделя 3) - НИЗКИЙ ПРИОРИТЕТ
- [ ] **8. Cleanup old persons** - 2ч
- [ ] **9. Защита от дубликатов** - 2ч
- [ ] **10. Webhook** - 3ч
- [ ] **12. Resolve TODOs** - 1ч

**Итого Sprint 3:** 8 часов = 1 рабочий день

### Sprint 4 (Неделя 4) - КАЧЕСТВО КОДА
- [ ] **11. Unit tests** - 8ч

**Итого Sprint 4:** 8 часов = 1 рабочий день

---

## 🎯 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

**После Sprint 1:**
- ✅ 100% визитов (Official + Student) поддерживаются
- ✅ Сотрудники получают уведомления о проходах
- ✅ Нет сбоев из-за невалидных person
- ✅ Нет 429 ошибок при массовых операциях

**После Sprint 2:**
- ✅ Security может мониторить гостей в реальном времени
- ✅ Ручное управление доступом через UI
- ✅ История проходов с фотофиксацией

**После Sprint 3:**
- ✅ HikCentral БД не засоряется старыми person'ами
- ✅ Нет дубликатов при повторных визитах
- ✅ Real-time обработка проходов (webhook)

**После Sprint 4:**
- ✅ Test coverage >70%
- ✅ Нет TODO в коде
- ✅ Production ready

---

## 📊 СТАТИСТИКА

**Всего функций в backlog:** 26
**Реализовано:** 9 (35%)
**Осталось:** 17 (65%)

**По приоритетам:**
- 🔴 Критические: 5/5 (100%) ✅
- 🟡 Высокие: 3/6 (50%)
- 🟠 Средние: 1/6 (17%)
- 🟢 Низкие: 0/9 (0%)

**Время на полную реализацию:** 36 часов = 4.5 рабочих дня

---

## 🚀 NEXT STEPS

1. **Согласовать приоритеты** с Product Owner
2. **Sprint 1:** Начать с StudentVisit support (блокирует 50% функционала для студентов)
3. **CI/CD:** Настроить автозапуск тестов после Sprint 4
4. **Документация:** Обновить API docs после каждого спринта

---

**Готовность к production:** 80% → 100% (после всех спринтов)

**Дата создания:** 2025-01-03  
**Автор:** AI Agent Analysis  
**Версия:** 1.0
