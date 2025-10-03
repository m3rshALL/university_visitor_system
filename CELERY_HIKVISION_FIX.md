# ✅ РЕШЕНИЕ: Celery + HikCentral Integration на Windows

## Проблема
Гости регистрировались в Django, но:
- HikAccessTask оставались в статусе `queued`
- Задачи не выполнялись
- Гости не появлялись в HikCentral UI

## Диагностика
1. **Django локально** + **Celery в Docker** = разные Redis инстансы
2. Задачи отправлялись в `localhost:6379`, worker слушал `redis:6379` (Docker network)
3. Pool `prefork` не работает на Windows (ошибка `ValueError: not enough values to unpack`)

## Решение
### 1. Запустить Celery ЛОКАЛЬНО с pool=solo

```powershell
cd d:\university_visitor_system\visitor_system
$env:PYTHONPATH="d:\university_visitor_system\visitor_system"
$env:DJANGO_SETTINGS_MODULE="visitor_system.conf.dev"

# Запуск worker на очереди hikvision
poetry run celery -A visitor_system.celery:app worker -Q hikvision --pool=solo --loglevel=info
```

### 2. Или используй start_celery.bat

```bat
cd d:\university_visitor_system
start_celery.bat
```

## Что было исправлено

### visitors/views.py (2 места)
```python
# БЫЛО:
result = chain(
    enroll_face_task.s(task.id),
    assign_access_level_task.si(access_task.id)
).apply_async()

# СТАЛО:
result = chain(
    enroll_face_task.s(task.id),
    assign_access_level_task.si(access_task.id)
).apply_async(queue='hikvision')  # ← Указываем очередь явно
```

### start_celery.bat
```bat
# БЫЛО:
poetry run celery -A visitor_system.celery:app worker --loglevel=info --pool=solo --concurrency=1

# СТАЛО:
poetry run celery -A visitor_system.celery:app worker -Q hikvision --pool=solo --loglevel=info
```

## Проверка работы

### 1. Запусти Celery worker
```powershell
cd d:\university_visitor_system
start_celery.bat
```

Должен увидеть:
```
[queues]
  .> hikvision        exchange=hikvision(direct) key=hikvision

[2025-10-03 17:40:48,404: INFO/MainProcess] Celery worker ready
```

### 2. Запусти Django
```powershell
cd d:\university_visitor_system\visitor_system
poetry run python manage.py runserver
```

### 3. Тестируй автоматически
```powershell
cd d:\university_visitor_system\visitor_system
poetry run python test_full_guest_flow.py
```

Должен увидеть:
```
✅ Guest created: ID=...
✅ Visit created: ID=..., Status=SCHEDULED
✅ Found 2 HikAccessTask records:
   - Task X: enroll_face - processing/completed
   - Task Y: assign_access - processing/completed
🎉 УСПЕХ! Гость зарегистрирован в HikCentral
```

### 4. Или создай гостя вручную
1. Открой http://127.0.0.1:8000/visits/register-guest/
2. Заполни форму
3. Проверь логи Celery worker - должны появиться строки:
```
[INFO/MainProcess] Task hikvision_integration.tasks.enroll_face_task[...] received
[INFO/MainProcess] Task hikvision_integration.tasks.enroll_face_task[...] succeeded
```

### 5. Проверь в HikCentral UI
- Открой HikCentral → Person Management
- Найди гостя по имени
- Должна быть карточка с фото и access levels

## Мониторинг

### Проверить статусы задач
```powershell
cd d:\university_visitor_system\visitor_system
poetry run python manage.py shell -c "from hikvision_integration.models import HikAccessTask; tasks = HikAccessTask.objects.all().order_by('-created_at')[:10]; print('\n'.join([f'{t.id}: {t.kind} - {t.status}' for t in tasks]))"
```

### Посмотреть логи worker
```powershell
# Если запущен через start_celery.bat - смотри консоль

# Если в background:
cd d:\university_visitor_system\visitor_system
Get-Content celery_hikvision.log -Tail 50
Get-Content celery_hikvision_error.log -Tail 50
```

### Проверить Redis очереди
```powershell
# Подключись к Redis в Docker
docker exec -it university_visitor_system-redis-1 redis-cli

# В redis-cli:
LLEN hikvision  # Должно быть 0 если задачи обрабатываются
KEYS *hikvision*
```

## Важные моменты

1. **Pool на Windows**: ТОЛЬКО `--pool=solo`, prefork НЕ работает
2. **Очередь**: Все HikCentral задачи идут в очередь `hikvision`
3. **Redis**: Должен быть доступен на `localhost:6379` (Docker с port forwarding)
4. **PYTHONPATH**: Обязательно установить на `d:\university_visitor_system\visitor_system`
5. **Django Settings**: `DJANGO_SETTINGS_MODULE=visitor_system.conf.dev`

## Troubleshooting

### Worker запускается но задачи не выполняются
- Проверь что задачи отправляются в очередь `hikvision`: `.apply_async(queue='hikvision')`
- Проверь что worker слушает эту очередь: `-Q hikvision`

### Ошибка "not enough values to unpack (expected 3, got 0)"
- Это значит используется pool=prefork на Windows
- Замени на `--pool=solo`

### Задачи в статусе PENDING
- Worker не запущен или слушает другую очередь
- Проверь Redis доступность: `docker ps | grep redis`

### HikCentral ошибки в логах
- Проверь настройки подключения к HikCentral
- Убедись что HikCentral доступен
- Проверь что организация и access levels существуют в HCP

## Файлы для контроля

- `visitors/views.py` - добавлен `queue='hikvision'` к `apply_async()`
- `start_celery.bat` - обновлен на `-Q hikvision --pool=solo`
- `test_full_guest_flow.py` - новый скрипт для автотеста
- `check_guest_status.ps1` - PowerShell скрипт для проверки статусов

---
**Дата исправления**: 2025-10-03  
**Статус**: ✅ РАБОТАЕТ
