# HikVision Worker Setup Guide

Руководство по запуску Celery worker для интеграции с HikCentral Professional.

## 📋 Prerequisites

Перед запуском убедитесь что установлены:

1. **Docker Desktop** - для Redis и PostgreSQL контейнеров
2. **Poetry** - для управления Python зависимостями
3. **Python 3.11+** - виртуальная среда через Poetry

## 🚀 Quick Start

### Вариант 1: Автоматический запуск (Рекомендуется)

Используйте готовые BAT скрипты:

```cmd
# 1. Запустить Redis
start_redis_docker.bat

# 2. Запустить PostgreSQL (если нужно)
start_postgres_docker.bat

# 3. Запустить Celery worker для HikVision
start_celery_hikvision_worker.bat
```

### Вариант 2: Ручной запуск

#### Шаг 1: Запустить Redis

Redis используется как Celery broker/backend.

**Проверить есть ли контейнер:**
```cmd
docker ps -a | findstr redis_celery
```

**Создать и запустить:**
```cmd
docker run -d --name redis_celery -p 6379:6379 redis:alpine
```

**Или стартовать существующий:**
```cmd
docker start redis_celery
```

**Проверить подключение:**
```cmd
docker exec redis_celery redis-cli ping
# Должно вернуть: PONG
```

#### Шаг 2: Запустить PostgreSQL (опционально)

Если БД не запущена на хосте:

```cmd
docker run -d --name postgres_visitor \
    -e POSTGRES_DB=visitor_system \
    -e POSTGRES_USER=visitor_user \
    -e POSTGRES_PASSWORD=visitor_pass \
    -p 5432:5432 \
    postgres:15-alpine
```

#### Шаг 3: Настроить .env

Убедитесь что `visitor_system/.env` содержит:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

# Database
POSTGRES_DB=visitor_system
POSTGRES_USER=visitor_user
POSTGRES_PASSWORD=visitor_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# HikCentral API
HIKVISION_HOST=your-hikvision-server
HIKVISION_APP_KEY=your-app-key
HIKVISION_APP_SECRET=your-app-secret
HIKVISION_TIMEZONE=Asia/Almaty
```

#### Шаг 4: Запустить Celery Worker

```cmd
cd d:\university_visitor_system\visitor_system

set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

poetry run celery -A visitor_system.celery:app worker ^
    -Q hikvision ^
    --pool=solo ^
    --loglevel=info ^
    --logfile=celery_hikvision.log ^
    -n hikvision_worker@%computername%
```

**Параметры:**
- `-Q hikvision` - слушать только очередь hikvision
- `--pool=solo` - Windows совместимый пул (без fork)
- `--loglevel=info` - уровень логирования
- `--logfile=...` - путь к файлу логов
- `-n worker_name@host` - имя worker

## 🔧 Проверка статуса

### Проверить все сервисы

```cmd
check_services_status.bat
```

Или вручную:

```cmd
# Redis
docker ps | findstr redis_celery

# PostgreSQL
docker ps | findstr postgres_visitor

# Celery workers
tasklist | findstr celery
```

### Мониторинг логов

**Real-time логи Celery:**
```cmd
cd visitor_system
Get-Content celery_hikvision.log -Tail 50 -Wait
```

**Логи ошибок:**
```cmd
Get-Content celery_hikvision_error.log -Tail 50
```

**Фильтр по задаче:**
```cmd
Get-Content celery_hikvision.log | Select-String "assign_access"
```

## 🧪 Тестирование

### Проверить что worker работает

```cmd
cd visitor_system
set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

poetry run python -c "from visitor_system.celery import app; i = app.control.inspect(); print(i.active_queues())"
```

**Ожидаемый результат:**
```python
{'hikvision_worker@DESKTOP-XXX': [{'name': 'hikvision', ...}]}
```

### Отправить тестовую задачу

```cmd
poetry run python -c "import django; django.setup(); from hikvision_integration.tasks import enroll_face_task; result = enroll_face_task.apply_async(args=[123], queue='hikvision'); print(f'Task ID: {result.id}')"
```

Проверить результат:
```cmd
poetry run celery -A visitor_system.celery:app result <task-id>
```

## 🛑 Остановка сервисов

### Остановить всё

```cmd
stop_all_services.bat
```

Или вручную:

```cmd
# Остановить Celery
taskkill /F /IM celery.exe

# Остановить контейнеры
docker stop redis_celery postgres_visitor
```

## 📊 Мониторинг задач (Flower)

Опционально можно запустить Flower для веб-интерфейса:

```cmd
poetry run celery -A visitor_system.celery:app flower --port=5555
```

Открыть в браузере: http://localhost:5555

## 🐛 Troubleshooting

### Проблема: "No module named 'visitor_system'"

**Решение:** Убедитесь что рабочая директория `visitor_system/` (где manage.py):
```cmd
cd d:\university_visitor_system\visitor_system
```

### Проблема: "Connection refused" для Redis

**Проверить:**
```cmd
docker ps | findstr redis_celery
```

**Решение:**
```cmd
docker start redis_celery
# или
start_redis_docker.bat
```

### Проблема: Task failed with "Person not found"

**Причины:**
1. Visit не имеет `hikcentral_person_id`
2. Person был удалён из HikCentral UI

**Проверить Visit:**
```python
poetry run python manage.py shell
>>> from visitors.models import Visit
>>> v = Visit.objects.get(id=XXX)
>>> print(v.hikcentral_person_id)
```

### Проблема: "Hikcentral Database Exception" (code=5)

**Причина:** HikCentral БД заполнена

**Решение:** Очистить БД в HikCentral UI:
1. Войти в HikCentral Professional
2. System → Database → Clear old records
3. Или удалить старые фото через Person Management

### Проблема: Photo не появляется в HikCentral

**Проверить:**
1. БД HikCentral имеет свободное место
2. Photo существует в `media/guest_photos/`
3. Task `enroll_face` завершился успешно

**Логи задачи:**
```python
poetry run python -c "import django; django.setup(); from hikvision_integration.models import HikAccessTask; t = HikAccessTask.objects.filter(visit_id=XXX, kind='enroll_face').first(); print(f'Status: {t.status}'); print(f'Error: {t.last_error}' if t.last_error else 'No error')"
```

### Проблема: Access не назначается (status=None)

**Исправлено в версии:** Текущая (после фикса)

Старые версии могли падать с ошибкой:
```
Person XXX is not active (status=None). Cannot assign access level.
```

**Решение:** Обновить код до текущей версии где валидация статуса опциональная:
```python
# services.py line 438
if person_status is not None and person_status != 1:
    raise RuntimeError(...)
```

## 📝 Логи и дебаг

### Уровни логирования

- `--loglevel=debug` - все сообщения (очень подробно)
- `--loglevel=info` - информационные (рекомендуется)
- `--loglevel=warning` - только предупреждения и ошибки
- `--loglevel=error` - только ошибки

### Формат логов

**Успешная задача:**
```
[2025-10-03 19:13:03,066: INFO] HikCentral: Found person_id=8551 from Visit.hikcentral_person_id
[2025-10-03 19:13:03,126: INFO] HikCentral: Person 8551 validation passed (status not returned by API)
[2025-10-03 19:13:03,180: INFO] HikCentral: addPersons response code=0 msg=Success
[2025-10-03 19:13:03,208: INFO] HikCentral: Visit 195 marked as access_granted=True
[2025-10-03 19:13:03,230: INFO] Task succeeded in 0.204s
```

**Ошибка:**
```
[2025-10-03 18:00:00,000: ERROR] HikCentral: Failed to upload face: code=5 msg=Hikcentral Database Exception
[2025-10-03 18:00:00,100: WARNING] Task will retry in 60s (attempt 1/3)
```

## 📚 Полезные команды

### Django shell для дебага

```cmd
cd visitor_system
poetry run python manage.py shell
```

```python
# Проверить Visit
from visitors.models import Visit
v = Visit.objects.get(id=195)
print(f"Person ID: {v.hikcentral_person_id}")
print(f"Access granted: {v.access_granted}")
print(f"Status: {v.status}")

# Проверить задачи
from hikvision_integration.models import HikAccessTask
tasks = HikAccessTask.objects.filter(visit_id=195).order_by('created_at')
for t in tasks:
    print(f"{t.id}: {t.kind} - {t.status}")
    if t.last_error:
        print(f"  Error: {t.last_error}")

# Проверить person binding
from hikvision_integration.models import HikPersonBinding
binding = HikPersonBinding.objects.filter(visit_id=195).first()
if binding:
    print(f"Person: {binding.person_id}, Face: {binding.face_id}, Status: {binding.status}")
```

### Retry failed task

```python
from hikvision_integration.tasks import assign_access_level_task
result = assign_access_level_task.apply_async(args=[65], queue='hikvision')
print(f"Task queued: {result.id}")
```

### Очистить все задачи из очереди

```cmd
poetry run celery -A visitor_system.celery:app purge
```

## 🎯 Best Practices

1. **Всегда проверяйте Redis** перед запуском worker
2. **Мониторьте логи** в реальном времени при тестировании
3. **Используйте retry** для failed задач вместо ручного исправления
4. **Проверяйте БД HikCentral** - главная причина сбоев при загрузке фото
5. **Используйте `--pool=solo`** на Windows (обязательно)

## 📞 Support

Если проблема не решается:
1. Проверьте логи `celery_hikvision.log` и `celery_hikvision_error.log`
2. Запустите `check_services_status.bat`
3. Проверьте Django shell для данных Visit/Task
4. Проверьте свободное место в БД HikCentral

---

**Последнее обновление:** 2025-01-03  
**Версия:** 1.0  
**Статус:** Все баги исправлены, production ready ✅
