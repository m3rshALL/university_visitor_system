# 🚀 Гайд: Запуск HikVision Integration Worker

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Требования](#требования)
3. [Запуск сервисов](#запуск-сервисов)
4. [Остановка сервисов](#остановка-сервисов)
5. [Проверка статуса](#проверка-статуса)
6. [Решение проблем](#решение-проблем)
7. [Логи и мониторинг](#логи-и-мониторинг)

---

## 🏃 Быстрый старт

### Вариант 1: Запуск только Worker (Redis и PostgreSQL уже запущены)

```batch
start_hikvision_worker.bat
```

### Вариант 2: Запуск полного стека (все сервисы)

```batch
start_full_stack.bat
```

### Проверка статуса

```batch
check_status.bat
```

### Остановка всех сервисов

```batch
stop_all.bat
```

---

## 📦 Требования

### 1. Docker Desktop
- **Установлен и запущен**: Docker Desktop должен работать
- **WSL2** (для Windows): Рекомендуется для лучшей производительности
- Проверка: `docker --version`

### 2. Python + Poetry
- **Python 3.11+**: Установлен на системе
- **Poetry**: Менеджер зависимостей Python
- Проверка: `poetry --version`

### 3. Зависимости проекта
- Установлены через Poetry: `poetry install`
- Виртуальное окружение активировано

---

## 🔧 Запуск сервисов

### 📌 Вариант 1: Полный стек (рекомендуется для разработки)

**Скрипт**: `start_full_stack.bat`

**Что запускается**:
1. ✅ Redis (localhost:6379) - Broker для Celery
2. ✅ PostgreSQL (localhost:5432) - База данных
3. ✅ Celery Worker - Обработка задач HikVision

**Запуск**:
```batch
# Двойной клик на файл или в командной строке:
start_full_stack.bat
```

**Окно останется открытым** - не закрывайте его, пока работаете с системой!

---

### 📌 Вариант 2: Только Worker (для продакшн)

**Скрипт**: `start_hikvision_worker.bat`

**Требования**:
- ✅ Redis уже запущен
- ✅ PostgreSQL уже запущен

**Запуск вручную Redis + PostgreSQL**:
```batch
docker-compose up -d redis db
```

**Затем запуск Worker**:
```batch
start_hikvision_worker.bat
```

---

### 📌 Вариант 3: Запуск через Docker Compose (альтернатива)

**Если хотите все в Docker**:

```batch
# Запуск всех сервисов в фоне
docker-compose up -d

# Просмотр логов worker
docker-compose logs -f celery-worker

# Остановка
docker-compose down
```

---

## 🛑 Остановка сервисов

### Способ 1: Скрипт (рекомендуется)

```batch
stop_all.bat
```

**Что останавливается**:
- ❌ Celery Workers (все процессы)
- ❌ Redis контейнер
- ❌ PostgreSQL контейнер

**Опционально**: Скрипт спросит - удалить контейнеры или только остановить.

---

### Способ 2: Вручную

**Остановка Worker**:
- Нажмите `Ctrl+C` в окне worker
- ИЛИ закройте окно терминала

**Остановка Docker контейнеров**:
```batch
docker-compose stop redis db
# или полная остановка:
docker-compose down
```

---

## ✅ Проверка статуса

### Скрипт проверки

```batch
check_status.bat
```

**Что проверяется**:
1. ✅ **Docker контейнеры**: Запущены ли Redis и PostgreSQL
2. ✅ **Celery Worker**: Работает ли процесс
3. ✅ **Redis**: Отвечает ли на ping
4. ✅ **PostgreSQL**: Готов ли принимать соединения
5. ✅ **Логи**: Последние 10 строк лога worker
6. ✅ **Очередь**: Активные задачи в Celery

---

### Ручная проверка

**Проверка Docker контейнеров**:
```batch
docker-compose ps
```

Ожидаемый результат:
```
NAME                                  STATUS
university_visitor_system-redis-1     Up 5 minutes
university_visitor_system-db-1        Up 5 minutes
```

**Проверка Celery Worker**:
```batch
tasklist | findstr celery.exe
```

Ожидаемый результат:
```
celery.exe    12345 Console    1     123,456 K
```

**Проверка Redis**:
```batch
docker exec -it university_visitor_system-redis-1 redis-cli ping
```

Ожидаемый результат:
```
PONG
```

**Проверка PostgreSQL**:
```batch
docker exec -it university_visitor_system-db-1 pg_isready -U visitor_user
```

Ожидаемый результат:
```
/var/run/postgresql:5432 - accepting connections
```

---

## 📊 Логи и мониторинг

### Файлы логов

**Celery Worker логи**:
- 📄 `visitor_system/celery_hikvision.log` - Основной лог (INFO)
- 📄 `visitor_system/celery_hikvision_error.log` - Только ошибки (ERROR)

**Просмотр логов в реальном времени**:

```powershell
# Windows PowerShell
Get-Content visitor_system\celery_hikvision.log -Wait -Tail 50

# Или только ошибки
Get-Content visitor_system\celery_hikvision_error.log -Wait -Tail 20
```

### Мониторинг задач

**Flower (Web UI для Celery)**:

```batch
cd visitor_system
poetry run celery -A visitor_system.celery:app flower --port=5555
```

Откройте: http://localhost:5555

**Командная строка**:

```batch
cd visitor_system

# Активные задачи
poetry run celery -A visitor_system.celery:app inspect active

# Зарегистрированные задачи
poetry run celery -A visitor_system.celery:app inspect registered

# Статистика
poetry run celery -A visitor_system.celery:app inspect stats
```

---

## 🔧 Решение проблем

### ❌ Проблема: Worker не запускается

**Симптомы**:
```
Error: Failed to connect to Redis
```

**Решение**:
1. Проверьте что Redis запущен:
   ```batch
   docker-compose ps redis
   ```
2. Если не запущен:
   ```batch
   docker-compose up -d redis
   ```
3. Проверьте порт 6379:
   ```batch
   netstat -an | findstr 6379
   ```

---

### ❌ Проблема: "Database Exception" при загрузке фото

**Симптомы**:
```
code=5 msg=Service exception. Hikcentral Database Exception
```

**Решение**:
1. **Проверьте БД HikCentral** - возможно переполнена
2. **Очистите старые фото** в HikCentral UI:
   - Person Management → Select persons with photos
   - Delete old/unused persons
3. **Проверьте лимиты лицензии** HikCentral

---

### ❌ Проблема: Worker "зависает" на Windows

**Симптомы**:
- Worker не обрабатывает задачи
- Нет логов

**Решение**:
Используйте `--pool=solo` (уже включен в скриптах):
```batch
poetry run celery -A visitor_system.celery:app worker -Q hikvision --pool=solo
```

---

### ❌ Проблема: Порт 6379 уже занят

**Симптомы**:
```
Error starting userland proxy: listen tcp 0.0.0.0:6379: bind: Only one usage of each socket address
```

**Решение**:
1. Проверьте что запущено на порту:
   ```batch
   netstat -ano | findstr :6379
   ```
2. Остановите другой Redis или измените порт в `docker-compose.yml`:
   ```yaml
   redis:
     ports:
       - "6380:6379"  # Новый порт
   ```
3. Обновите `visitor_system/visitor_system/conf/dev.py`:
   ```python
   CELERY_BROKER_URL = 'redis://localhost:6380/0'
   ```

---

### ❌ Проблема: "permission denied" при запуске скрипта

**Симптомы**:
```
Access is denied
```

**Решение**:
1. Запустите **PowerShell/CMD от имени администратора**
2. ИЛИ измените права на папку:
   ```batch
   icacls "D:\university_visitor_system" /grant %USERNAME%:F /T
   ```

---

## 🎯 Рабочий процесс (Daily Usage)

### Утро (начало работы):

1. **Запустите Docker Desktop** (если еще не запущен)
2. **Запустите full stack**:
   ```batch
   start_full_stack.bat
   ```
3. **Проверьте статус**:
   ```batch
   check_status.bat
   ```

### В течение дня:

- **Worker работает в фоне** - не закрывайте окно!
- **Задачи обрабатываются автоматически** при регистрации гостей
- **Проверяйте логи** периодически:
  ```batch
  check_status.bat
  ```

### Вечер (конец работы):

1. **Остановите все сервисы**:
   ```batch
   stop_all.bat
   ```
2. **Опционально**: Оставьте Redis и PostgreSQL запущенными (выберите "No" при удалении контейнеров)

---

## 📝 Настройки конфигурации

### Redis настройки

**Файл**: `visitor_system/visitor_system/conf/dev.py`

```python
# Celery Broker (Redis)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
    }
}
```

### PostgreSQL настройки

**Файл**: `docker-compose.yml`

```yaml
db:
  image: postgres:15
  environment:
    POSTGRES_DB: visitor_db
    POSTGRES_USER: visitor_user
    POSTGRES_PASSWORD: visitor_pass
  ports:
    - "5432:5432"
```

**Connection string**:
```
postgresql://visitor_user:visitor_pass@localhost:5432/visitor_db
```

---

## 🆘 Поддержка

**Проблемы с Worker**:
- Проверьте `celery_hikvision_error.log`
- Запустите `check_status.bat`

**Проблемы с Redis**:
```batch
docker logs university_visitor_system-redis-1
```

**Проблемы с PostgreSQL**:
```batch
docker logs university_visitor_system-db-1
```

**Вопросы**:
- Проверьте документацию в `.github/copilot-instructions.md`
- Ищите похожие проблемы в `HIKVISION_GAPS_ANALYSIS.md`

---

## ✨ Полезные команды

```batch
# Рестарт Redis
docker-compose restart redis

# Рестарт PostgreSQL
docker-compose restart db

# Просмотр логов Redis
docker logs -f university_visitor_system-redis-1

# Подключение к PostgreSQL
docker exec -it university_visitor_system-db-1 psql -U visitor_user -d visitor_db

# Очистка старых задач в Redis
docker exec -it university_visitor_system-redis-1 redis-cli FLUSHALL

# Просмотр всех ключей в Redis
docker exec -it university_visitor_system-redis-1 redis-cli KEYS "*"
```

---

## 📚 Дополнительные материалы

- **Celery документация**: https://docs.celeryproject.org/
- **Redis документация**: https://redis.io/documentation
- **Docker Compose**: https://docs.docker.com/compose/

---

**Версия**: 1.0  
**Дата**: 2025-10-03  
**Автор**: AI Assistant

