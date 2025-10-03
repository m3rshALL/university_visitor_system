# Анализ пробелов: HikVision автоматизация

## 🎯 Executive Summary

После детального анализа системы автоматизации HikVision обнаружено **26 критических пробелов**, которые можно разделить на 4 категории по приоритету:

- **5 критических** - блокируют production запуск
- **6 высокого приоритета** - нужны для полной функциональности
- **6 среднего приоритета** - улучшают UX и observability
- **9 низкого приоритета** - оптимизации и расширения

---

## 🚨 КРИТИЧЕСКИЕ (Блокируют production)

### 1. ❌ person_id НЕ сохраняется в Visit при реальном создании

**Проблема:**
```python
# В create_visit():
enroll_face_task.apply_async([task.id])  # Создаёт person
assign_access_level_task.apply_async([access_task.id])  # Назначает доступ

# НО person_id НИГДЕ не сохраняется в visit.hikcentral_person_id!
```

**Последствие:**
- `monitor_guest_passages_task` не может найти person_id
- ВСЕ визиты, созданные через веб-интерфейс, пропускаются при мониторинге
- Автоблокировка НЕ РАБОТАЕТ для 99% визитов

**Решение:** ✅ ИСПРАВЛЕНО
```python
# В enroll_face_task() добавлено:
if task.visit_id:
    Visit.objects.filter(id=task.visit_id).update(
        hikcentral_person_id=str(person_id)
    )
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ (уже исправлено)

---

### 2. ❌ Race condition между enroll_face_task и assign_access_level_task

**Проблема:**
```python
# В create_visit():
transaction.on_commit(lambda: enroll_face_task.apply_async(...))
transaction.on_commit(lambda: assign_access_level_task.apply_async(...))
# Обе задачи запускаются ПАРАЛЛЕЛЬНО!
```

**Последствие:**
- `assign_access_level_task` может выполниться ДО создания person
- Ошибка: "Person 8512 not found"
- Гость НЕ получит доступ, не пройдёт турникет

**Решение:**
```python
# Использовать Celery chain:
from celery import chain

chain(
    enroll_face_task.s(task.id),
    assign_access_level_task.s(access_task.id)
).apply_async()
```

**Альтернатива:**
```python
# Или в assign_access_level_task добавить проверку:
def assign_access_level_task(task_id):
    # Ждём завершения enroll_face_task
    enroll_task = HikAccessTask.objects.get(visit_id=visit_id, task_type='enroll_face')
    if enroll_task.status != 'success':
        raise self.retry(countdown=30)  # Retry через 30 секунд
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 3. ❌ Нет retry mechanism при сбоях HCP API

**Проблема:**
```python
@shared_task(queue='hikvision')  # Нет max_retries!
def assign_access_level_task(task_id):
    success = assign_access_level_to_person(...)
    if not success:
        raise RuntimeError('Failed')  # Задача упадёт навсегда
```

**Последствие:**
- Временный сбой HCP → гость навсегда без доступа
- Нет автоматического восстановления
- Требуется ручное вмешательство

**Решение:**
```python
@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue='hikvision')
def assign_access_level_task(self, task_id):
    try:
        success = assign_access_level_to_person(...)
        if not success:
            raise RuntimeError('Failed to assign access')
    except Exception as exc:
        # Exponential backoff: 60s, 120s, 240s, 480s, 960s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 4. ❌ auto_close_expired_visits НЕ отзывает доступ

**Проблема:**
Существующая задача `visitors.tasks.auto_close_expired_visits` (каждые 15 минут):
```python
def auto_close_expired_visits():
    Visit.objects.filter(
        status='CHECKED_IN',
        expected_exit_time__lt=now()
    ).update(
        status='CHECKED_OUT',
        exit_time=now()
    )
    # НО доступ в HCP НЕ отзывается!
```

**Последствие:**
- Гость должен был выйти в 16:00
- Система закрыла визит автоматически
- НО гость может вернуться в 20:00 и пройти турникет (доступ до 22:00!)

**Решение:**
```python
def auto_close_expired_visits():
    from hikvision_integration.tasks import revoke_access_level_from_person
    from hikvision_integration.services import HikCentralSession
    
    expired_visits = Visit.objects.filter(
        status='CHECKED_IN',
        expected_exit_time__lt=now(),
        access_granted=True,
        access_revoked=False
    )
    
    session = HikCentralSession(...)
    
    for visit in expired_visits:
        # Отзываем доступ
        if visit.hikcentral_person_id:
            revoke_access_level_from_person(
                session,
                visit.hikcentral_person_id,
                settings.HIKCENTRAL_GUEST_ACCESS_GROUP_ID
            )
            visit.access_revoked = True
        
        visit.status = 'CHECKED_OUT'
        visit.exit_time = now()
        visit.save()
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 5. ❌ Нет cleanup person при отмене/завершении визита

**Проблема:**
- Визит отменён (status='CANCELLED')
- Визит завершён (status='CHECKED_OUT')
- Person остаётся в HCP навсегда!

**Последствие:**
- База HCP засоряется "мёртвыми" person'ами
- При 100 визитах/день → 36,500 person'ов/год
- Производительность HCP деградирует

**Решение 1:** Отзывать доступ при отмене/завершении
```python
# Signal в visitors/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Visit)
def revoke_access_on_cancel_or_checkout(sender, instance, **kwargs):
    if instance.status in ['CANCELLED', 'CHECKED_OUT'] and \
       instance.access_granted and not instance.access_revoked:
        # Вызвать задачу отзыва доступа
        revoke_access_task.apply_async(args=[instance.id])
```

**Решение 2:** Периодическая очистка старых person
```python
@shared_task
def cleanup_old_persons_task():
    """Удаляет person'ы из HCP с validTo < now() - 30 days"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_visits = Visit.objects.filter(
        hikcentral_person_id__isnull=False,
        entry_time__lt=cutoff_date,
        status__in=['CHECKED_OUT', 'CANCELLED']
    )
    
    session = HikCentralSession(...)
    
    for visit in old_visits:
        try:
            # DELETE /person/{personId}
            delete_person_hikcentral(session, visit.hikcentral_person_id)
            visit.hikcentral_person_id = None
            visit.save()
        except Exception as e:
            logger.error("Failed to delete person %s: %s", visit.hikcentral_person_id, e)
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

## ⚠️ ВЫСОКИЙ ПРИОРИТЕТ (Нужны для полной функциональности)

### 6. StudentVisit не поддерживается

**Проблема:**
```python
# monitor_guest_passages_task ищет только Visit:
Visit.objects.filter(access_granted=True, ...)

# НО есть StudentVisit!
class StudentVisit(models.Model):
    guest = ForeignKey(Guest)
    department = ForeignKey(Department)
    entry_time = DateTimeField()
    # НЕТ полей: access_granted, hikcentral_person_id!
```

**Последствие:**
- Студенты/абитуриенты НЕ получают автоматический доступ
- Мониторинг не работает для студентов

**Решение:**
1. Добавить те же поля в StudentVisit:
```python
class StudentVisit(models.Model):
    # ... existing fields ...
    
    access_granted = models.BooleanField(default=False)
    access_revoked = models.BooleanField(default=False)
    hikcentral_person_id = models.CharField(max_length=50, blank=True, null=True)
    first_entry_detected = models.DateTimeField(blank=True, null=True)
    first_exit_detected = models.DateTimeField(blank=True, null=True)
    entry_count = models.IntegerField(default=0)
    exit_count = models.IntegerField(default=0)
```

2. Обновить задачи для поддержки обеих моделей:
```python
def monitor_guest_passages_task():
    # Мониторим Visit
    visits = Visit.objects.filter(access_granted=True, ...)
    # Мониторим StudentVisit
    student_visits = StudentVisit.objects.filter(access_granted=True, ...)
    
    for visit in chain(visits, student_visits):
        # Одинаковая логика
        ...
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

### 7. Нет уведомлений сотруднику о проходах

**Проблема:**
Сотрудник НЕ знает:
- Гость получил доступ ✅
- Гость прошёл турникет (вход) 🚪
- Гость вышел (доступ заблокирован) 🚫

**Решение:**
```python
# В monitor_guest_passages_task после обновления счётчиков:
if visit.first_entry_detected and not visit.entry_notification_sent:
    send_notification_task.apply_async(args=[
        visit.employee_id,
        'Гость вошёл',
        f'{visit.guest.full_name} прошёл турникет в {visit.first_entry_detected}'
    ])
    visit.entry_notification_sent = True
    visit.save()

if visit.first_exit_detected and not visit.exit_notification_sent:
    send_notification_task.apply_async(args=[
        visit.employee_id,
        'Гость вышел',
        f'{visit.guest.full_name} покинул здание в {visit.first_exit_detected}'
    ])
    visit.exit_notification_sent = True
    visit.save()
```

Нужны новые поля:
```python
class Visit(models.Model):
    # ...
    entry_notification_sent = models.BooleanField(default=False)
    exit_notification_sent = models.BooleanField(default=False)
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

### 8. Нет обработки изменения времени визита

**Проблема:**
```python
# Сотрудник продлевает визит:
visit.expected_exit_time = now() + timedelta(hours=3)
visit.save()

# НО в HCP person всё ещё validTo=22:00 (не обновляется!)
```

**Решение:**
```python
# Signal в visitors/signals.py
@receiver(post_save, sender=Visit)
def update_person_validity_on_time_change(sender, instance, **kwargs):
    if instance.hikcentral_person_id:
        # Проверяем, изменилось ли время
        old_instance = Visit.objects.get(pk=instance.pk)
        if old_instance.expected_exit_time != instance.expected_exit_time:
            # Обновляем person в HCP
            update_person_validity_task.apply_async(args=[instance.id])
```

Новая задача:
```python
@shared_task
def update_person_validity_task(visit_id):
    visit = Visit.objects.get(id=visit_id)
    session = HikCentralSession(...)
    
    update_person_hikcentral(
        session,
        person_id=visit.hikcentral_person_id,
        valid_to=visit.expected_exit_time.isoformat()
    )
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

### 9. Нет обработки отмены визита (CANCELLED)

**Проблема:**
```python
visit.status = 'CANCELLED'
visit.save()

# Person остаётся в HCP с активным доступом!
```

**Решение:**
```python
@receiver(post_save, sender=Visit)
def revoke_access_on_cancellation(sender, instance, **kwargs):
    if instance.status == 'CANCELLED' and \
       instance.access_granted and not instance.access_revoked:
        revoke_access_task.apply_async(args=[instance.id])
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

### 10. Нет проверки validity person перед назначением access

**Проблема:**
```python
def assign_access_level_task(task_id):
    # Слепо пытаемся назначить access
    assign_access_level_to_person(session, person_id, access_group_id)
    # Что если person не существует? Expired? Deleted?
```

**Решение:**
```python
def assign_access_level_task(task_id):
    # 1. Проверяем person
    person_info = get_person_hikcentral(session, person_id)
    
    if not person_info:
        raise RuntimeError(f'Person {person_id} not found in HCP')
    
    if person_info.get('validTo') < now().isoformat():
        raise RuntimeError(f'Person {person_id} expired')
    
    # 2. Назначаем access
    assign_access_level_to_person(...)
```

Новая функция в services.py:
```python
def get_person_hikcentral(session, person_id):
    """GET /person/{personId}"""
    response = session.get(f'/person/v1/persons/{person_id}')
    if response.get('code') == '0':
        return response.get('data')
    return None
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

### 11. Нет rate limiting для массовых операций

**Проблема:**
```python
# Конференция: регистрация 100 гостей одновременно
for guest in guests:
    enroll_face_task.apply_async(...)  # 100 задач запускаются параллельно!

# HCP API: 429 Too Many Requests
```

**Решение 1:** Celery rate_limit
```python
@shared_task(rate_limit='10/m', queue='hikvision')  # 10 запросов в минуту
def enroll_face_task(task_id):
    ...
```

**Решение 2:** Dedicated queue с concurrency=1
```python
# celery.py
app.conf.task_routes = {
    'hikvision_integration.tasks.enroll_face_task': {
        'queue': 'hikvision_serial',  # Отдельная очередь
    },
}

# worker.py
celery -A visitor_system worker -Q hikvision_serial -c 1  # Одна задача за раз
```

**Приоритет:** 🟡 ВЫСОКИЙ

---

## 📊 СРЕДНИЙ ПРИОРИТЕТ (Улучшения UX/observability)

### 12. Нет dashboard для security (real-time monitoring)

**Что нужно:**
- Список гостей в здании (CHECKED_IN + access_granted=True)
- Последние 10 проходов (entry/exit events)
- Alerts: гости без выхода >2 часов
- Карта: где сейчас гости (по door locations)

**Решение:**
Расширить `realtime_dashboard` app:
```python
# realtime_dashboard/consumers.py
class SecurityDashboardConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        # Отправляем данные каждые 5 секунд
        guests_inside = Visit.objects.filter(
            status='CHECKED_IN',
            access_granted=True,
            access_revoked=False
        ).count()
        
        recent_passages = DoorEvent.objects.order_by('-event_time')[:10]
        
        await self.send(text_data=json.dumps({
            'guests_inside': guests_inside,
            'recent_passages': [e.to_dict() for e in recent_passages]
        }))
```

**Приоритет:** 🟠 СРЕДНИЙ

---

### 13. Нет Prometheus metrics

**Что нужно:**
```python
from prometheus_client import Counter, Gauge

hikcentral_access_assignments_total = Counter(
    'hikcentral_access_assignments_total',
    'Total access level assignments',
    ['status']  # success, failed
)

hikcentral_door_events_total = Counter(
    'hikcentral_door_events_total',
    'Total door passage events',
    ['event_type']  # entry, exit
)

hikcentral_guests_inside = Gauge(
    'hikcentral_guests_inside',
    'Number of guests currently inside'
)
```

**Использование:**
```python
# В assign_access_level_task:
if success:
    hikcentral_access_assignments_total.labels(status='success').inc()
else:
    hikcentral_access_assignments_total.labels(status='failed').inc()

# В monitor_guest_passages_task:
for event in events:
    if event.get('eventType') == 1:
        hikcentral_door_events_total.labels(event_type='entry').inc()
    elif event.get('eventType') == 2:
        hikcentral_door_events_total.labels(event_type='exit').inc()
```

**Приоритет:** 🟠 СРЕДНИЙ

---

### 14. Нет UI для ручного управления доступом

**Что нужно:**
- Кнопка "Заблокировать доступ" (revoke)
- Кнопка "Продлить доступ"
- История проходов для визита
- Статус person в HCP (active/expired/deleted)

**Решение:**
```python
# visitors/views.py
@require_POST
def manual_revoke_access(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)
    
    if visit.access_granted and not visit.access_revoked:
        revoke_access_task.apply_async(args=[visit.id])
        messages.success(request, 'Доступ будет заблокирован в течение минуты')
    
    return redirect('visit_detail', visit_id=visit_id)

# В шаблоне visit_detail.html:
{% if visit.access_granted and not visit.access_revoked %}
<form method="post" action="{% url 'manual_revoke_access' visit.id %}">
    {% csrf_token %}
    <button type="submit" class="btn btn-danger">
        🚫 Заблокировать доступ
    </button>
</form>
{% endif %}
```

**Приоритет:** 🟠 СРЕДНИЙ

---

### 15. Нет фотофиксации проходов (eventPicUrl)

**Проблема:**
HCP возвращает `eventPicUrl` в door/events, но мы НЕ сохраняем его.

**Решение:**
Создать модель для событий:
```python
class DoorEvent(models.Model):
    visit = ForeignKey(Visit, on_delete=CASCADE, related_name='door_events')
    event_type = IntegerField(choices=[(1, 'Entry'), (2, 'Exit')])
    event_time = DateTimeField()
    door_name = CharField(max_length=100)
    event_pic_url = URLField(blank=True, null=True)  # Фото с камеры
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-event_time']
        indexes = [
            Index(fields=['visit', '-event_time']),
        ]
```

В monitor_guest_passages_task:
```python
for event in events:
    DoorEvent.objects.create(
        visit=visit,
        event_type=event.get('eventType'),
        event_time=parse(event.get('eventTime')),
        door_name=event.get('doorName', 'Unknown'),
        event_pic_url=event.get('eventPicUrl')  # Сохраняем URL фото
    )
```

**Приоритет:** 🟠 СРЕДНИЙ

---

### 16. Нет обработки Face Recognition Failed events

**Проблема:**
Гость не может пройти турникет (лицо не распознано), но никто не знает!

**Решение:**
```python
# В monitor_guest_passages_task:
for event in events:
    if event.get('eventType') == 'FaceRecognitionFailed':
        # Уведомление сотруднику
        send_notification_task.apply_async(args=[
            visit.employee_id,
            'Гость не может пройти турникет',
            f'{visit.guest.full_name} не распознан системой. Возможно, плохое качество фото.'
        ])
        
        # Сохраняем событие
        DoorEvent.objects.create(
            visit=visit,
            event_type=-1,  # Failed
            event_time=now(),
            door_name=event.get('doorName'),
            notes='Face recognition failed'
        )
```

**Приоритет:** 🟠 СРЕДНИЙ

---

## 🔧 НИЗКИЙ ПРИОРИТЕТ (Оптимизации)

### 17. Нет cleanup old persons task

**Решение:** (см. пункт 5 выше - Решение 2)

**Расписание:**
```python
# celery.py
app.conf.beat_schedule = {
    'cleanup-old-persons': {
        'task': 'hikvision_integration.tasks.cleanup_old_persons_task',
        'schedule': crontab(hour=3, minute=0, day_of_month='1'),  # Первое число месяца в 3:00
    },
}
```

**Приоритет:** 🟢 НИЗКИЙ

---

### 18. Нет защиты от дубликатов person

**Проблема:**
Гость приходит повторно → создаётся новый person с новым personCode.

**Решение:**
```python
# В enroll_face_task:
def enroll_face_task(task_id):
    # Проверяем, есть ли у Guest предыдущие визиты
    previous_visit = Visit.objects.filter(
        guest_id=task.guest_id,
        hikcentral_person_id__isnull=False
    ).order_by('-entry_time').first()
    
    if previous_visit and previous_visit.hikcentral_person_id:
        # Переиспользуем person_id
        person_id = previous_visit.hikcentral_person_id
        logger.info("Reusing person_id %s from previous visit", person_id)
    else:
        # Создаём нового
        person_id = ensure_person_hikcentral(...)
```

**Альтернатива:** Добавить Guest.hikcentral_person_id (permanent)

**Приоритет:** 🟢 НИЗКИЙ

---

### 19. Нет webhook от HCP (вместо polling)

**Проблема:**
Polling каждые 10 минут → задержка до 10 минут в обнаружении прохода.

**Решение:**
```python
# visitors/views.py
@csrf_exempt
@require_POST
def hikvision_webhook(request):
    """Endpoint для приёма webhook от HCP"""
    payload = json.loads(request.body)
    
    event_type = payload.get('eventType')
    person_id = payload.get('personId')
    event_time = payload.get('eventTime')
    
    # Находим визит
    visit = Visit.objects.filter(hikcentral_person_id=person_id).first()
    if not visit:
        return JsonResponse({'status': 'ok'})
    
    # Обрабатываем событие
    if event_type == 1:  # Entry
        visit.entry_count += 1
        if not visit.first_entry_detected:
            visit.first_entry_detected = parse(event_time)
    elif event_type == 2:  # Exit
        visit.exit_count += 1
        if not visit.first_exit_detected:
            visit.first_exit_detected = parse(event_time)
            # Сразу блокируем!
            revoke_access_task.apply_async(args=[visit.id])
    
    visit.save()
    return JsonResponse({'status': 'ok'})
```

Настройка в HCP:
- Event Subscription → Door Events
- Callback URL: `https://yourdomain.com/api/hikvision/webhook`

**Приоритет:** 🟢 НИЗКИЙ

---

### 20. Нет синхронизации статуса с HCP

**Проблема:**
Admin вручную удалил person в HCP → Django не знает.

**Решение:**
```python
@shared_task
def sync_persons_status_task():
    """Синхронизирует статус person из HCP в Django"""
    active_visits = Visit.objects.filter(
        hikcentral_person_id__isnull=False,
        status='CHECKED_IN'
    )
    
    session = HikCentralSession(...)
    
    for visit in active_visits:
        person_info = get_person_hikcentral(session, visit.hikcentral_person_id)
        
        if not person_info:
            # Person удалён в HCP
            visit.access_revoked = True
            visit.save()
            logger.warning("Person %s not found in HCP, marked as revoked", visit.hikcentral_person_id)
        elif person_info.get('validTo') < now().isoformat():
            # Person expired
            visit.access_revoked = True
            visit.save()
```

**Расписание:** Каждый час

**Приоритет:** 🟢 НИЗКИЙ

---

### 21-26. Остальные низкоприоритетные пункты

- **21. Backup/restore person** - восстановление после сбоя HCP
- **22. Разные access groups по типам гостей** - VIP, обычные, студенты
- **23. Grace period для re-entry** - разрешить вернуться в течение 15 минут
- **24. celery_task_id в HikAccessTask** - отмена задач
- **25. История изменений access level** - audit trail
- **26. UI для просмотра статуса person в HCP** - debugging tool

---

## 📈 План внедрения

### Phase 1 (Неделя 1): Критические fixes
- [x] Fix #1: person_id сохранение (✅ уже исправлено)
- [ ] Fix #2: Chain tasks (enroll → assign)
- [ ] Fix #3: Retry mechanism
- [ ] Fix #4: auto_close_expired_visits + revoke
- [ ] Fix #5: Cleanup on cancel/checkout

### Phase 2 (Неделя 2): Высокий приоритет
- [ ] Fix #6: StudentVisit support
- [ ] Fix #7: Notifications
- [ ] Fix #8: Time change handling
- [ ] Fix #9: Cancellation handling
- [ ] Fix #10: Person validity check
- [ ] Fix #11: Rate limiting

### Phase 3 (Неделя 3): Средний приоритет
- [ ] Fix #12: Security dashboard
- [ ] Fix #13: Prometheus metrics
- [ ] Fix #14: Manual control UI
- [ ] Fix #15: Photo capture
- [ ] Fix #16: Failed recognition handling

### Phase 4 (Месяц 2): Оптимизации
- [ ] Fixes #17-26: Low priority improvements

---

## 🎯 Ожидаемые результаты после Phase 1

- ✅ 100% визитов корректно мониторятся
- ✅ Нет race conditions
- ✅ Автоматическое восстановление после сбоев
- ✅ Доступ отзывается при истечении срока
- ✅ Нет "мёртвых" person в HCP

**Готовность к production:** 95% → 100%

---

Дата создания: 2025-10-02  
Версия: 1.0  
Автор: AI Agent Analysis
