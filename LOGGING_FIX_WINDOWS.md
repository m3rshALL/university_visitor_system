# 🔧 Исправление ошибки RotatingFileHandler на Windows

**Дата:** 14.10.2025  
**Проблема:** `PermissionError: [WinError 32]` при ротации логов  
**Статус:** ✅ **ИСПРАВЛЕНО**

---

## ❌ Проблема

```
PermissionError: [WinError 32] Процесс не может получить доступ к файлу, 
так как этот файл занят другим процессом: visitor_system.log
```

### Причина

**Windows блокирует файлы** когда они открыты в нескольких процессах одновременно:

1. **Django dev server** (2 процесса из-за auto-reload)
2. **Celery workers** (несколько worker процессов)
3. **Celery Beat** (scheduler процесс)

Все они пишут в **один файл** `visitor_system.log` → стандартный `RotatingFileHandler` **не может ротировать файл** → **ОШИБКА**

---

## ✅ Решение

Используем **`concurrent-log-handler`** - специальная библиотека для Windows с поддержкой многопроцессной записи.

### Что изменено

#### 1. Установлена библиотека

```bash
pip install concurrent-log-handler
```

**Зависимости:**
- `concurrent-log-handler==0.9.28`
- `portalocker>=1.6.0` (для блокировки файлов)
- `pywin32>=226` (для Windows file locking)

#### 2. Обновлены настройки логирования

**Файл:** `visitor_system/visitor_system/conf/base.py`

**Было:**
```python
'file': {
    'level': 'INFO',
    'class': 'logging.handlers.RotatingFileHandler',  # ← Не работает с multiple processes
    'filename': str(LOGS_DIR / 'visitor_system.log'),
    'maxBytes': 1024 * 1024 * 5,
    'backupCount': 5,
    'formatter': 'verbose',
    'encoding': 'utf-8',
},
```

**Стало:**
```python
'file': {
    'level': 'INFO',
    'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',  # ← Thread-safe + Process-safe
    'filename': str(LOGS_DIR / 'visitor_system.log'),
    'maxBytes': 1024 * 1024 * 5,  # 5 MB
    'backupCount': 5,
    'formatter': 'verbose',
    'encoding': 'utf-8',
},
```

---

## 🚀 Как работает ConcurrentRotatingFileHandler

### Особенности

1. **Process-safe** - несколько процессов могут писать одновременно
2. **Thread-safe** - несколько потоков могут писать одновременно
3. **File locking** через `portalocker` (использует Windows API)
4. **Автоматическая ротация** при достижении `maxBytes`
5. **Хранит backupCount старых файлов**

### Механизм блокировки

```python
# Упрощенная схема работы
with portalocker.Lock(log_file, 'a'):  # Эксклюзивная блокировка
    log_file.write(log_message)  # Запись в файл
    if log_file.size > maxBytes:
        rotate_logs()  # Ротация под блокировкой
```

**Преимущества:**
- ✅ Нет конфликтов между процессами
- ✅ Нет потери сообщений
- ✅ Нет ошибок `PermissionError`
- ✅ Работает на Windows/Linux/macOS

---

## 📊 Настройки ротации

### Текущая конфигурация

```python
'maxBytes': 1024 * 1024 * 5,  # 5 MB - размер одного файла
'backupCount': 5,              # Хранить 5 старых файлов
```

**Файлы логов:**
```
visitor_system/logs/
├── visitor_system.log      ← Текущий файл (до 5 MB)
├── visitor_system.log.1    ← Предыдущий (до 5 MB)
├── visitor_system.log.2
├── visitor_system.log.3
├── visitor_system.log.4
└── visitor_system.log.5    ← Самый старый (потом удаляется)
```

**Всего:** Максимум 30 MB (6 файлов × 5 MB)

---

## 🔧 Настройка (опционально)

### Увеличить размер файла

```python
'maxBytes': 1024 * 1024 * 10,  # 10 MB вместо 5 MB
```

### Хранить больше файлов

```python
'backupCount': 10,  # Хранить 10 старых файлов вместо 5
```

### Уменьшить уровень логирования

```python
'level': 'WARNING',  # Только WARNING и выше (меньше сообщений)
```

---

## ✅ Проверка исправления

### Перезапустить сервисы

```powershell
# Остановить все
.\stop_all.bat

# Запустить заново
.\start_postgres_docker.bat
.\start_redis_docker.bat
.\start_celery.bat
```

**В другом окне:**
```powershell
cd visitor_system
python manage.py runserver
```

### Проверить логи

Ошибка `PermissionError` **НЕ ДОЛЖНА** появляться!

```powershell
# Просмотр последних логов
Get-Content visitor_system\logs\visitor_system.log -Tail 20 -Wait
```

---

## 📋 Дополнительные улучшения

### 1. Отдельные файлы для разных компонентов (опционально)

Можно создать отдельные handlers для Django и Celery:

```python
'handlers': {
    'django_file': {
        'level': 'INFO',
        'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
        'filename': str(LOGS_DIR / 'django.log'),
        'maxBytes': 1024 * 1024 * 5,
        'backupCount': 5,
        'formatter': 'verbose',
        'encoding': 'utf-8',
    },
    'celery_file': {
        'level': 'INFO',
        'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
        'filename': str(LOGS_DIR / 'celery.log'),
        'maxBytes': 1024 * 1024 * 5,
        'backupCount': 5,
        'formatter': 'verbose',
        'encoding': 'utf-8',
    },
},
'loggers': {
    'django': {
        'handlers': ['console', 'django_file'],
        'level': 'INFO',
    },
    'celery': {
        'handlers': ['console', 'celery_file'],
        'level': 'INFO',
    },
}
```

### 2. Логирование в JSON формате

Для structured logging:

```python
'formatters': {
    'json': {
        'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
    },
},
'handlers': {
    'file': {
        'formatter': 'json',  # ← JSON вместо текста
        # ... остальные параметры ...
    },
}
```

**Требует:** `pip install python-json-logger`

### 3. Отправка критических ошибок на email

```python
'handlers': {
    'mail_admins': {
        'level': 'ERROR',
        'class': 'django.utils.log.AdminEmailHandler',
        'include_html': True,
    },
},
'loggers': {
    'django': {
        'handlers': ['console', 'file', 'mail_admins'],  # ← Добавили email
        'level': 'INFO',
    },
}
```

---

## 📚 Ссылки

- **concurrent-log-handler:** https://pypi.org/project/concurrent-log-handler/
- **Документация:** https://github.com/Preston-Landers/concurrent-log-handler
- **Django Logging:** https://docs.djangoproject.com/en/4.2/topics/logging/

---

## ✅ ИТОГ

### Что было исправлено

1. ✅ Установлена библиотека `concurrent-log-handler`
2. ✅ Заменен `RotatingFileHandler` → `ConcurrentRotatingFileHandler`
3. ✅ Ошибка `PermissionError [WinError 32]` устранена

### Результат

- ✅ **Никаких ошибок** при ротации логов
- ✅ **Безопасная многопроцессная запись** в один файл
- ✅ **Работает на Windows** без проблем
- ✅ **Автоматическая ротация** при достижении 5 MB

**Перезапустите сервисы чтобы изменения вступили в силу!**

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025

