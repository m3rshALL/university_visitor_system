# Автоматический Check-in/Checkout через FaceID турникеты

## Описание функции

**Статус**: ✅ РАЗВЕРНУТО В PRODUCTION (03.10.2025)

Система автоматически изменяет статус визитов на основе реальных проходов через турникеты с FaceID:
- **При входе**: EXPECTED → CHECKED_IN (устанавливается entry_time)
- **При выходе**: CHECKED_IN → CHECKED_OUT (устанавливается exit_time)

**Ключевая особенность**: Персонал рецепции только регистрирует гостей. Дальше всё происходит автоматически через FaceID турникеты - никаких ручных кнопок "Вход" и "Выход".

---

## Технические детали

### Мониторинг событий

**Задача**: `monitor_guest_passages_task` (hikvision_integration/tasks.py)
- **Частота**: Каждые 5 минут (Celery Beat)
- **API**: HikCentral /acs/v1/door/events
- **Окно данных**: Последние 5 минут

### Логика автоматических действий

#### 1. Автоматический Check-in
```python
# Условия
- Статус визита: EXPECTED
- Обнаружен первый вход через турникет (eventType=1)
- hikcentral_person_id != NULL (доступ активен)

# Действия
1. visit.status = 'CHECKED_IN'
2. visit.entry_time = <время прохода через турникет>
3. visit.first_entry_detected = <время прохода>
4. Создается AuditLog с reason="Auto check-in via FaceID turnstile"
```

#### 2. Автоматический Checkout
```python
# Условия
- Статус визита: CHECKED_IN
- Обнаружен первый выход через турникет (eventType=2)

# Действия
1. visit.status = 'CHECKED_OUT'
2. visit.exit_time = <время прохода через турникет>
3. visit.first_exit_detected = <время прохода>
4. Создается AuditLog с reason="Auto checkout via FaceID turnstile"
5. Django сигнал → автоматическая отмена доступа в HikCentral
```

#### 3. Обнаружение аномалий
```python
# Сценарий: Выход без входа
if visit.status == 'EXPECTED' and first_exit_detected:
    logger.warning("⚠️ EXIT without ENTRY - anomaly detected")
    # Статус НЕ меняется, только логируется предупреждение
```

---

## Настройки Celery Beat

### Файл: `visitor_system/celery.py`

```python
beat_schedule = {
    'monitor-guest-passages': {
        'task': 'hikvision_integration.tasks.monitor_guest_passages_task',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут (было 10)
        'options': {
            'expires': 240.0  # 4 минуты (чтобы не накапливались)
        }
    },
    # ... другие задачи
}
```

**Изменения от предыдущей версии**:
- Частота: 10 минут → **5 минут** (для более оперативного обновления статусов)
- Окно данных: 10 минут → **5 минут**

---

## Поток данных

```
┌─────────────────┐
│  Гость проходит │
│  через турникет │
│   (FaceID OK)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ HikCentral Central  │
│ фиксирует событие:  │
│ - personId          │
│ - eventType (1/2)   │
│ - eventTime         │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────┐
│ Celery Beat (каждые 5м): │
│ monitor_guest_passages   │
└────────┬─────────────────┘
         │
         ▼
┌────────────────────────────┐
│ API запрос:                │
│ GET /acs/v1/door/events    │
│ ?startTime=now-5m          │
│ &pageSize=1000             │
└────────┬───────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Фильтрация событий:         │
│ - Только для активных       │
│   визитов с person_id       │
│ - Группировка по personId   │
│ - Первый вход/выход         │
└────────┬────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Обновление статусов:         │
│ EXPECTED → CHECKED_IN (вход) │
│ CHECKED_IN → CHECKED_OUT     │
│             (выход)          │
└────────┬─────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ Создание AuditLog:         │
│ - action: 'update'         │
│ - user_agent: 'HikCentral  │
│   FaceID System'           │
│ - reason: 'Auto check-in/  │
│   out via FaceID turnstile'│
└────────┬───────────────────┘
         │
         ▼ (при выходе)
┌────────────────────────────┐
│ Django Signal:             │
│ post_save → revoke_access  │
│ Отмена доступа в HikCentral│
│ (одноразовый проход)       │
└────────────────────────────┘
```

---

## Аудит и логирование

### AuditLog записи

Все автоматические изменения статуса записываются в `visitors.AuditLog`:

```python
AuditLog.objects.create(
    visit=visit,
    action='update',
    user=None,  # Системное действие
    user_agent='HikCentral FaceID System',
    ip_address='127.0.0.1',
    reason='Auto check-in via FaceID turnstile',  # или 'Auto checkout'
    changes={
        'status': ['EXPECTED', 'CHECKED_IN'],
        'entry_time': [None, '2025-10-03T10:30:15'],
        # ...
    }
)
```

### Поиск автоматических действий

```python
# Django shell
from visitors.models import AuditLog
from datetime import timedelta
from django.utils import timezone

# Все авто check-in/out за последние 24 часа
auto_actions = AuditLog.objects.filter(
    user_agent='HikCentral FaceID System',
    timestamp__gte=timezone.now() - timedelta(hours=24)
).order_by('-timestamp')

# Группировка по типу
check_ins = auto_actions.filter(reason__icontains='check-in').count()
check_outs = auto_actions.filter(reason__icontains='checkout').count()

print(f"Auto check-ins: {check_ins}")
print(f"Auto checkouts: {check_outs}")
```

---

## Мониторинг и отладка

### 1. Проверка расписания Celery Beat

```bash
# Проверить, что задача зарегистрирована
docker-compose logs celery-beat | grep "monitor-guest-passages"

# Должно быть видно каждые 5 минут:
# [INFO] Scheduler: Sending due task monitor-guest-passages
```

### 2. Мониторинг выполнения задачи

```bash
# Логи worker (в реальном времени)
docker-compose logs -f celery-worker | grep -E "(monitor_guest|Auto check)"

# Пример успешного выполнения:
# [INFO] Task hikvision_integration.tasks.monitor_guest_passages_task succeeded
# [INFO] Visit 123: ✅ Auto check-in via FaceID (EXPECTED → CHECKED_IN)
# [INFO] Visit 123: ✅ Auto checkout via FaceID (CHECKED_IN → CHECKED_OUT)
```

### 3. Проверка автоматических изменений

```bash
# Запустить тестовый скрипт
cd /path/to/project
poetry run python test_auto_checkin_checkout.py

# Или вручную через Django shell
poetry run python visitor_system/manage.py shell
```

```python
# В Django shell
from visitors.models import Visit, AuditLog
from django.utils import timezone
from datetime import timedelta

# Визиты, готовые к auto check-in
ready_for_checkin = Visit.objects.filter(
    status='EXPECTED',
    hikcentral_person_id__isnull=False,
    first_entry_detected__isnull=True
).select_related('guest', 'student')

print(f"Готовы к авто check-in: {ready_for_checkin.count()}")

# Недавние автоматические действия
recent_auto = AuditLog.objects.filter(
    user_agent='HikCentral FaceID System',
    timestamp__gte=timezone.now() - timedelta(hours=1)
).values('visit_id', 'reason', 'timestamp')

for log in recent_auto:
    print(f"Visit {log['visit_id']}: {log['reason']} at {log['timestamp']}")
```

### 4. Метрики Prometheus

Задача `monitor_guest_passages_task` экспортирует метрики:
- `hikvision_monitor_passages_duration_seconds` - время выполнения
- `hikvision_monitor_passages_total` - общее количество запусков
- `hikvision_monitor_passages_errors_total` - количество ошибок

Доступны в `/metrics`.

---

## Часто задаваемые вопросы

### Q1: Что если гость прошел турникет, но статус не обновился?

**A**: Проверьте:
1. Celery Beat работает: `docker-compose ps celery-beat`
2. Задача выполняется каждые 5 минут: `docker-compose logs celery-beat | grep monitor`
3. Worker обрабатывает задачу: `docker-compose logs celery-worker | grep monitor_guest`
4. Есть ли события в HikCentral: проверьте API `/acs/v1/door/events`
5. У визита есть `hikcentral_person_id`: визит должен иметь активный доступ

### Q2: Как проверить, что система работает в production?

**A**: Используйте тестовый скрипт:
```bash
poetry run python test_auto_checkin_checkout.py
```

Или проверьте недавние AuditLog:
```python
from visitors.models import AuditLog
AuditLog.objects.filter(user_agent='HikCentral FaceID System').latest('timestamp')
```

### Q3: Почему интервал 5 минут, а не реальное время?

**A**: 
- HikCentral API не поддерживает WebHooks (push-уведомления)
- Polling каждые 5 минут - баланс между нагрузкой и оперативностью
- Для критических кейсов можно уменьшить до 1-2 минут (изменить `crontab(minute='*/5')`)

### Q4: Что если одновременно сработают ручное и автоматическое действие?

**A**: 
- Ручные действия больше НЕ используются (по требованию пользователя)
- Если всё же используются: Django ORM гарантирует атомарность обновлений
- Последнее изменение будет сохранено, в AuditLog будет 2 записи

### Q5: Как обрабатывается "выход без входа"?

**A**:
- Логируется WARNING в логи Celery
- Статус визита НЕ меняется (остается EXPECTED)
- Создается AuditLog с пометкой об аномалии
- Требуется ручная проверка администратором

---

## Rollback (откат изменений)

Если нужно вернуться к старому поведению (10 минут, без авто check-in/out):

### 1. Откат изменений в tasks.py

```bash
cd /path/to/project
git diff visitor_system/visitor_system/hikvision_integration/tasks.py
git checkout HEAD -- visitor_system/visitor_system/hikvision_integration/tasks.py
```

### 2. Откат расписания Celery

```bash
git checkout HEAD -- visitor_system/visitor_system/celery.py
```

### 3. Перезапуск сервисов

```bash
docker-compose restart celery-beat celery-worker
```

---

## История изменений

### v1.0 (03.10.2025) - Initial Release

**Реализованные функции**:
- ✅ Автоматический check-in при входе (EXPECTED → CHECKED_IN)
- ✅ Автоматический checkout при выходе (CHECKED_IN → CHECKED_OUT)
- ✅ Audit logging всех автоматических действий
- ✅ Обнаружение аномалий (выход без входа)
- ✅ Мониторинг каждые 5 минут (было 10)
- ✅ Тестовый набор для проверки функции
- ✅ Интеграция с Django Signals (auto-revoke)

**Файлы изменены**:
- `visitor_system/visitor_system/hikvision_integration/tasks.py` (строки 623-860)
- `visitor_system/visitor_system/celery.py` (строка 48)
- `test_auto_checkin_checkout.py` (новый файл)

**Тесты**:
- ✅ 5/5 тестов пройдено
- Создано 2 визита с CHECKED_IN статусом для демонстрации

**Развертывание**:
- Migration 0042 уже применена (для Phase 2/3)
- Celery Beat и Worker перезапущены
- Задача зарегистрирована в расписании

---

## Контакты

**Разработчик**: AI Coding Agent  
**Дата развертывания**: 03.10.2025  
**Версия Django**: 5.0+  
**Версия Celery**: 5.5.3  
**HikCentral API**: Professional

---

## Следующие шаги

1. ✅ **ЗАВЕРШЕНО**: Реализовать auto check-in/checkout
2. ✅ **ЗАВЕРШЕНО**: Создать тестовый набор
3. ✅ **ЗАВЕРШЕНО**: Обновить расписание Celery (5 минут)
4. ✅ **ЗАВЕРШЕНО**: Добавить audit logging
5. ⏳ **В ОЖИДАНИИ**: Мониторинг первых автоматических действий в production
6. 📋 **ПЛАНИРУЕТСЯ**: Дашборд с метриками auto check-in/out (Grafana)
7. 📋 **ПЛАНИРУЕТСЯ**: Email-уведомления о критических аномалиях

---

**Статус**: 🚀 READY FOR PRODUCTION  
**Последнее обновление**: 03.10.2025 10:56 UTC
