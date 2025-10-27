# 🚀 Celery Quick Start - Исправление "No active workers"

**Дата:** 14.10.2025  
**Проблема:** `"status": "warning", "message": "No active workers detected"`  
**Решение:** ✅ Запустить Celery Workers

---

## ⚡ БЫСТРЫЙ СТАРТ

### Вариант 1: Запустить ВСЁ (рекомендуется)

```bash
# Запустит все Celery сервисы в отдельных окнах
start_celery_all.bat
```

Это запустит:
- ✅ Celery Worker (default) - для backup и общих задач
- ✅ Celery Worker (hikvision) - для HikVision интеграции
- ✅ Celery Beat (scheduler) - для автоматических задач по расписанию

---

### Вариант 2: Запустить только основной Worker

```bash
# Только для backup и общих задач
start_celery_default.bat
```

---

### Вариант 3: Запустить вручную (для разработки)

```bash
cd visitor_system
poetry run celery -A visitor_system.celery:app worker --pool=solo --loglevel=info
```

---

## 🔍 ПРОВЕРКА

После запуска проверьте health:

```bash
# Browser
http://localhost:8000/health/

# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health/"

# cURL
curl http://localhost:8000/health/
```

**Ожидаемый результат (✅ Healthy):**
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok"},
    "redis": {"status": "ok"},
    "celery": {
      "status": "ok",
      "workers": 1,
      "worker_names": ["celery@HOSTNAME"]
    }
  }
}
```

---

## 📊 КАКОЙ WORKER ДЛЯ ЧЕГО?

### 1. Default Worker (`start_celery_default.bat`)
**Обрабатывает:**
- ⚠️ **Database backups** (критично!)
- Auto-close expired visits
- Cleanup old audit logs
- Security events analysis
- Daily audit reports
- Email notifications

**Когда нужен:** ВСЕГДА для production

---

### 2. HikVision Worker (`start_celery_hikvision_worker.bat`)
**Обрабатывает:**
- Face enrollment в HikCentral
- Access level assignment
- Monitor guest passages
- Auto check-in/out
- HikVision API calls

**Когда нужен:** Если используете HikVision интеграцию

---

### 3. Celery Beat (`start_celery_beat.bat`)
**Запускает по расписанию:**
- Database backup (ежедневно в 3:00)
- Auto-close visits (каждые 15 мин)
- Monitor passages (каждые 5 мин)
- Cleanup logs (ежедневно в 2:00)
- Audit reports (ежедневно в 6:00)

**Когда нужен:** Для автоматических задач по расписанию

---

## 🛠️ TROUBLESHOOTING

### Проблема: Worker запускается и сразу закрывается

**Решение:**
```bash
# Проверить что Redis запущен
docker ps | findstr redis

# Если нет - запустить
start_redis_docker.bat
```

---

### Проблема: "ModuleNotFoundError"

**Решение:**
```bash
# Установить зависимости
poetry install

# Проверить что в правильной директории
cd visitor_system
```

---

### Проблема: "Connection refused" к Redis

**Решение:**
```bash
# 1. Запустить Redis
start_redis_docker.bat

# 2. Проверить что порт 6379 открыт
netstat -an | findstr 6379

# 3. Проверить настройки в settings.py
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
```

---

### Проблема: Worker запущен, но tasks не выполняются

**Решение:**
```bash
# 1. Проверить логи worker
# Ищите ERROR или WARNING в окне worker

# 2. Проверить что task в правильной очереди
# Default tasks → default worker
# HikVision tasks → hikvision worker

# 3. Перезапустить worker
# Закрыть окно и запустить заново
```

---

## 📝 ЛОГИ

### Где смотреть логи:

**Worker logs:**
- В окне терминала где запущен worker
- `visitor_system/logs/visitor_system.log`
- `visitor_system/celery_hikvision.log` (для HikVision)

**Beat logs:**
- В окне терминала где запущен beat
- Показывает когда задачи отправлены

**Django logs:**
- `visitor_system/logs/visitor_system.log`

---

## 🔄 АВТОЗАПУСК (Production)

Для production настройте автозапуск через:

### 1. Windows Service (рекомендуется)
```bash
# Используйте NSSM (Non-Sucking Service Manager)
# https://nssm.cc/

nssm install CeleryWorker
# Path: D:\university_visitor_system\start_celery_default.bat

nssm install CeleryBeat
# Path: D:\university_visitor_system\start_celery_beat.bat
```

### 2. Task Scheduler (альтернатива)
- Откройте Task Scheduler
- Create Task → Trigger: "At system startup"
- Action: Start a program → `start_celery_all.bat`

---

## ✅ CHECKLIST

- [ ] Redis запущен (порт 6379)
- [ ] PostgreSQL запущен (порт 5432)
- [ ] Celery Worker (default) запущен
- [ ] Celery Beat запущен (для автоматических задач)
- [ ] Health check возвращает "healthy"
- [ ] Backup тест выполнен успешно

---

## 🧪 ТЕСТИРОВАНИЕ

### 1. Тест что worker работает:

```bash
# Django shell
cd visitor_system
poetry run python manage.py shell
```

```python
from visitors.tasks import backup_database_task

# Отправить задачу
result = backup_database_task.delay()

# Проверить результат через несколько секунд
print(result.ready())  # True если завершено
print(result.get())    # Результат задачи
```

---

### 2. Тест health check:

```bash
curl http://localhost:8000/health/ | python -m json.tool
```

Должно быть:
- `"status": "healthy"`
- `"celery": {"status": "ok", "workers": 1}`

---

### 3. Тест backup:

```bash
cd visitor_system
poetry run python manage.py backup_database
```

Проверить что создан файл в `backups/`

---

## 📞 ПОДДЕРЖКА

**Если проблема не решается:**

1. Проверьте логи в окне worker (красные ERROR сообщения)
2. Проверьте что Redis работает: `docker ps`
3. Перезапустите все сервисы:
   ```bash
   # Закрыть все Celery окна
   # Запустить заново
   start_celery_all.bat
   ```

---

## 🎯 ИТОГО

**Для исправления "No active workers":**

1. Запустите: `start_celery_all.bat`
2. Проверьте: `http://localhost:8000/health/`
3. Должно быть: `"status": "healthy"`

**Готово!** ✅

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025

