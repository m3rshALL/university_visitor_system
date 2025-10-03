# ⚡ Быстрый запуск HikVision Integration

## Для работы интеграции с HikCentral Professional

### 1️⃣ Запустить Redis

```cmd
start_redis_docker.bat
```

Или вручную:
```cmd
docker run -d --name redis_celery -p 6379:6379 redis:alpine
```

### 2️⃣ Запустить Celery Worker

```cmd
start_celery_hikvision_worker.bat
```

Или вручную:
```cmd
cd visitor_system
set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev
poetry run celery -A visitor_system.celery:app worker -Q hikvision --pool=solo --loglevel=info
```

### 3️⃣ Проверить статус

```cmd
check_services_status.bat
```

Или вручную:
```cmd
# Redis
docker ps | findstr redis_celery

# Celery workers
tasklist | findstr celery
```

### 4️⃣ Остановить всё

```cmd
stop_all_services.bat
```

---

## 📚 Документация

- **Полное руководство:** [HIKVISION_WORKER_SETUP.md](HIKVISION_WORKER_SETUP.md)
- **Список исправленных багов:** [HIKVISION_BUGS_FIXED.md](HIKVISION_BUGS_FIXED.md)
- **Основной README:** [README.md](README.md)

---

## ✅ Проверка работы

### Отправить тестовую задачу

```cmd
cd visitor_system
set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

poetry run python -c "import django; django.setup(); from hikvision_integration.tasks import enroll_face_task; result = enroll_face_task.apply_async(args=[123], queue='hikvision'); print(f'Task ID: {result.id}')"
```

### Мониторинг логов

```cmd
cd visitor_system
Get-Content celery_hikvision.log -Tail 50 -Wait
```

---

## 🐛 Troubleshooting

### Redis не запускается

```cmd
docker stop redis_celery
docker rm redis_celery
docker run -d --name redis_celery -p 6379:6379 redis:alpine
```

### Celery worker не запускается

1. Проверить что Redis работает
2. Проверить `.env` файл в `visitor_system/`
3. Убедиться что рабочая директория `visitor_system/` (где manage.py)
4. Использовать `--pool=solo` на Windows (обязательно!)

### Task падает с ошибкой

1. Проверить логи: `celery_hikvision.log` и `celery_hikvision_error.log`
2. Проверить Visit/Task в Django shell
3. Убедиться что HikCentral БД имеет свободное место

---

**Последнее обновление:** 2025-01-03  
**Статус:** ✅ Production Ready
