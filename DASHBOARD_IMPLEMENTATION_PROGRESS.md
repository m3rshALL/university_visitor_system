# Dashboard и Security Monitoring - Прогресс реализации

**Дата:** 14.10.2025  
**Метод:** Sequential Thinking  
**Статус:** 🟡 **В ПРОЦЕССЕ (70% готово)**

---

## ✅ ЧТО УЖЕ РЕАЛИЗОВАНО

### 1. Модель SecurityIncident ✅
**Файл:** `visitor_system/visitors/models.py` (строки 586-736)

**Функционал:**
- Хранение security incidents (аномалий)
- 6 типов инцидентов: exit_without_entry, long_stay, suspicious_time, multiple_failed_access, repeated_exit_entry, other
- 4 уровня severity: low, medium, high, critical
- 4 статуса: new, investigating, resolved, false_alarm
- Поля: visit, incident_type, severity, status, description, detected_at, resolved_at, assigned_to, alert_sent, metadata
- Методы: mark_resolved(), mark_false_alarm()

### 2. SecurityIncidentAdmin ✅
**Файл:** `visitor_system/visitors/admin.py` (строки 185-240)

**Функционал:**
- Управление инцидентами через Django Admin
- Фильтрация по типу, severity, status, дате
- Поиск по гостю, описанию, ID визита
- Actions: mark_as_resolved, mark_as_false_alarm, assign_to_me
- Readonly поля: detected_at, alert_sent_at

### 3. Детекция аномалий в monitor_guest_passages_task ✅
**Файл:** `visitor_system/hikvision_integration/tasks.py`

**Реализованные аномалии:**

#### 3.1 EXIT_WITHOUT_ENTRY (строки 950-988)
- Триггер: Обнаружен выход через турникет без предварительного входа
- Severity: HIGH
- Действие: Создается SecurityIncident + отправка alert

#### 3.2 LONG_STAY (строки 1040-1083)
- Триггер: Гость в здании более MAX_GUEST_STAY_HOURS (по умолчанию 8 часов)
- Severity: MEDIUM
- Проверка: Каждые 5 минут через monitor_guest_passages_task
- Настройка: `settings.MAX_GUEST_STAY_HOURS = 8`

#### 3.3 SUSPICIOUS_TIME (строки 1085-1127)
- Триггер: Вход в нерабочее время (до 6:00 или после 22:00)
- Severity: MEDIUM
- Настройки:
  - `settings.WORK_HOURS_START = 6`
  - `settings.WORK_HOURS_END = 22`

### 4. Security Alert System ✅
**Файлы:**
- `visitor_system/hikvision_integration/utils.py` - utility функции
- `visitor_system/hikvision_integration/tasks.py` - Celery task
- `templates/notifications/email/security_alert.html` - HTML email template

**Функционал:**
- Автоматическая отправка email alerts при обнаружении аномалий
- Celery task: `send_security_alert_task` (строки 1340-1373)
- Async wrapper: `send_security_alert_async(incident_id)`
- Sync fallback: `send_security_alert_sync(incident_id)`
- Красивый HTML email с информацией об инциденте
- Retry mechanism: 3 попытки с exponential backoff (60s, 120s, 240s)

**Получатели alerts:**
1. `settings.SECURITY_ADMIN_EMAILS` (приоритет)
2. `settings.ADMINS` (fallback)
3. Superusers с email (последний fallback)

### 5. Views для Dashboards ✅
**Файл:** `visitor_system/visitors/dashboards.py`

**Три dashboard view:**

#### 5.1 auto_checkin_dashboard
- Статистика автоматических check-in/checkout за период (день/неделя/месяц)
- График проходов по часам/дням
- Последние 20 автоматических действий
- Топ-10 недавних аномалий
- Текущие гости в здании
- Статистика по типам инцидентов

#### 5.2 security_incidents_dashboard
- Список инцидентов с фильтрацией
- Фильтры: status (active/all/resolved/false_alarm), severity, type
- Статистика: total, active, critical incidents
- Группировка по типам и severity
- Limit: 100 записей

#### 5.3 hikcentral_dashboard
- Список HikCentral серверов + статус доступности
- Статистика визитов с HikCentral интеграцией
- Автоматические check-in/checkout counts
- Rate limiter status (calls limit, current usage, available)
- Placeholder для recent errors

---

## 🟡 В ПРОЦЕССЕ РЕАЛИЗАЦИИ

### 6. HTML Templates для Dashboards 🔄
**Нужно создать:**
- `templates/visitors/auto_checkin_dashboard.html`
- `templates/visitors/security_incidents_dashboard.html`
- `templates/visitors/hikcentral_dashboard.html`

**Требования:**
- Responsive design (Bootstrap 5)
- Графики (Chart.js или аналог)
- Красивые карточки со статистикой
- Таблицы с фильтрацией
- Real-time обновление (опционально через HTMX/WebSockets)

### 7. URLs для Dashboards 🔄
**Нужно добавить в** `visitor_system/visitors/urls.py`:
```python
from .dashboards import (
    auto_checkin_dashboard,
    security_incidents_dashboard,
    hikcentral_dashboard
)

urlpatterns = [
    # ... existing patterns ...
    path('dashboards/auto-checkin/', auto_checkin_dashboard, name='auto_checkin_dashboard'),
    path('dashboards/security-incidents/', security_incidents_dashboard, name='security_incidents_dashboard'),
    path('dashboards/hikcentral/', hikcentral_dashboard, name='hikcentral_dashboard'),
]
```

### 8. Миграции базы данных 🔄
**Нужно создать и применить:**
```bash
cd visitor_system
python manage.py makemigrations visitors
python manage.py migrate visitors
```

**Изменения в БД:**
- Новая таблица: `visitors_securityincident`
- Индексы для быстрого поиска:
  - `incident_detected_idx` (detected_at DESC)
  - `incident_type_date_idx` (incident_type, detected_at DESC)
  - `incident_severity_status_idx` (severity, status)

---

## 📋 АРХИТЕКТУРА РЕШЕНИЯ

```
┌─────────────────────────────────────────────────────────────┐
│         monitor_guest_passages_task (Celery Beat)           │
│              Запускается каждые 5 минут                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─► Получает door events от HikCentral API
                 │
                 ├─► Обрабатывает автоматические check-in/out
                 │
                 └─► Детектирует аномалии:
                     │
                     ├─► EXIT_WITHOUT_ENTRY
                     │   └─► SecurityIncident.create(severity=HIGH)
                     │       └─► send_security_alert_async()
                     │
                     ├─► LONG_STAY (> 8 часов)
                     │   └─► SecurityIncident.create(severity=MEDIUM)
                     │       └─► send_security_alert_async()
                     │
                     └─► SUSPICIOUS_TIME (вне раб. часов)
                         └─► SecurityIncident.create(severity=MEDIUM)
                             └─► send_security_alert_async()

┌─────────────────────────────────────────────────────────────┐
│            send_security_alert_task (Celery)                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─► Загружает incident из БД
                 │
                 ├─► Получает список security admins
                 │
                 ├─► Формирует HTML email (красивый шаблон)
                 │
                 ├─► Отправляет email через SMTP
                 │
                 └─► Обновляет incident (alert_sent=True)

┌─────────────────────────────────────────────────────────────┐
│                  Dashboards (Web UI)                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─► auto_checkin_dashboard
                 │   ├─► Статистика за период
                 │   ├─► График по часам
                 │   ├─► Последние действия
                 │   └─► Топ аномалий
                 │
                 ├─► security_incidents_dashboard
                 │   ├─► Список инцидентов
                 │   ├─► Фильтры (status/severity/type)
                 │   └─► Статистика
                 │
                 └─► hikcentral_dashboard
                     ├─► Статус HCP серверов
                     ├─► Статистика интеграции
                     └─► Rate limiter status
```

---

## ⚙️ НАСТРОЙКИ В SETTINGS.PY

Добавить в `visitor_system/visitor_system/conf/base.py`:

```python
# Security Monitoring Settings
MAX_GUEST_STAY_HOURS = 8  # Максимальное время пребывания гостя
WORK_HOURS_START = 6      # Начало рабочего дня (час)
WORK_HOURS_END = 22       # Конец рабочего дня (час)

# Security Admin Emails (получатели security alerts)
SECURITY_ADMIN_EMAILS = [
    'security@example.com',
    'admin@example.com',
]

# Site URL для ссылок в email
SITE_URL = 'https://your-domain.com'
```

---

## 🧪 КАК ПРОТЕСТИРОВАТЬ

### 1. Создать миграции и применить
```bash
cd visitor_system
python manage.py makemigrations visitors
python manage.py migrate visitors
```

### 2. Проверить Django Admin
```
http://localhost:8000/admin/visitors/securityincident/
```

### 3. Симулировать аномалию EXIT_WITHOUT_ENTRY
```python
# В Django shell
from visitors.models import Visit, SecurityIncident
from django.utils import timezone

# Найти визит со статусом EXPECTED
visit = Visit.objects.filter(status='EXPECTED', access_granted=True).first()

# Симулировать exit event (обычно делает monitor_guest_passages_task)
incident = SecurityIncident.objects.create(
    visit=visit,
    incident_type=SecurityIncident.INCIDENT_EXIT_WITHOUT_ENTRY,
    severity=SecurityIncident.SEVERITY_HIGH,
    description='TEST: Exit without entry detected',
    metadata={'test': True}
)

# Проверить отправку alert
from hikvision_integration.utils import send_security_alert_sync
send_security_alert_sync(incident.id)
```

### 4. Проверить автоматическую детекцию
- Запустить Celery Beat
- Создать визит с HikCentral интеграцией
- Дождаться monitor_guest_passages_task (каждые 5 мин)
- Проверить логи и SecurityIncident в админке

---

## 📊 МЕТРИКИ И МОНИТОРИНГ

### Dashboard Metrics (auto_checkin_dashboard)
- **Auto Check-ins Today:** Количество автоматических входов
- **Auto Checkouts Today:** Количество автоматических выходов
- **Guests Inside:** Текущие гости в здании
- **Incidents Today:** Количество инцидентов за сегодня
- **Chart:** График проходов по часам (check-in vs checkout)

### Security Metrics (security_incidents_dashboard)
- **Total Incidents:** Всего инцидентов
- **Active Incidents:** Активные (new + investigating)
- **Critical Incidents:** Критические и нерешенные
- **By Type:** Группировка по типам аномалий
- **By Severity:** Группировка по уровню важности

### HikCentral Metrics (hikcentral_dashboard)
- **HCP Servers Status:** Доступность серверов
- **Total with HikCentral:** Визиты с интеграцией
- **Active with Access:** Активные с доступом
- **Auto Check-ins:** Автоматических входов всего
- **Auto Checkouts:** Автоматических выходов всего
- **Rate Limiter:** Текущее использование (calls/window)

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### Высокий приоритет
1. ✅ Создать HTML templates для dashboards
2. ✅ Добавить URLs routing
3. ✅ Создать и применить миграции
4. ✅ Протестировать отправку security alerts

### Средний приоритет
5. ⚡ Добавить SMS alerts (через Twilio или аналог)
6. ⚡ Real-time updates для dashboards (WebSockets/HTMX)
7. ⚡ Export в Excel/PDF для отчетов
8. ⚡ Scheduling для регулярных отчетов (daily/weekly digest)

### Низкий приоритет
9. 💡 Machine Learning для предсказания аномалий
10. 💡 Integration с другими security системами
11. 💡 Mobile app для security admins
12. 💡 Telegram bot для instant alerts

---

## 📝 ИТОГ

### Статус: 70% готово ✅

**Реализовано:**
- ✅ Модель SecurityIncident с полным функционалом
- ✅ Django Admin для управления инцидентами
- ✅ Автоматическая детекция 3 типов аномалий
- ✅ Email alert system с красивыми шаблонами
- ✅ 3 dashboard views с аналитикой
- ✅ Utility функции и Celery tasks

**Осталось:**
- 🔄 HTML templates для dashboards (30% работы)
- 🔄 URLs routing (5 минут)
- 🔄 Миграции БД (5 минут)
- 🔄 Тестирование и отладка

**Время до завершения:** ~2-3 часа работы

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025  
**Метод:** Sequential Thinking

