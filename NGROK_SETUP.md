# Запуск приложения через ngrok

## ⚠️ ВАЖНО: Решение ошибки ERR_NGROK_3200

Если вы видите ошибку **"ERR_NGROK_3200 - Tunnel not found"** или **"Call internal services from your gateway"**, это означает, что ngrok не может правильно проксировать запросы к localhost без специального флага.

**Решение:** Используйте флаг `--host-header` при запуске ngrok!

## Быстрый старт (ПРАВИЛЬНЫЙ способ)

### 🚀 Способ 1: Автоматический (рекомендуется)

**Шаг 1:** Запустите ngrok через готовый скрипт
```powershell
.\start_ngrok.bat
```

Этот скрипт автоматически запустит ngrok с правильными параметрами.

**Шаг 2:** Скопируйте URL из вывода ngrok
Например: `https://cb9f6715124a.ngrok-free.app`

**Шаг 3:** В **новом терминале** запустите Django
```powershell
.\start_with_ngrok.bat https://cb9f6715124a.ngrok-free.app
```

**Шаг 4:** Откройте сайт в браузере
Используйте URL из ngrok. При первом посещении нажмите "Visit Site" на странице предупреждения ngrok.

### 🛠️ Способ 2: Ручной запуск

**Шаг 1:** Запустите ngrok **с флагом --host-header** (в первом терминале)
```powershell
ngrok http 8000 --host-header=localhost:8000
```

**ВАЖНО!** Без флага `--host-header=localhost:8000` вы получите ошибку ERR_NGROK_3200!

Вы увидите что-то вроде:
```text
Forwarding  https://cb9f6715124a.ngrok-free.app -> http://localhost:8000
```

**Шаг 2:** Скопируйте URL ngrok
Скопируйте URL из вывода ngrok (например, `cb9f6715124a.ngrok-free.app` или полный URL `https://cb9f6715124a.ngrok-free.app`)

**Шаг 3:** Запустите Django (во втором терминале)
```powershell
.\start_with_ngrok.bat cb9f6715124a.ngrok-free.app
```

или с полным URL:
```powershell
.\start_with_ngrok.bat https://cb9f6715124a.ngrok-free.app
```

**Шаг 4:** Откройте сайт
Откройте браузер и перейдите по URL из ngrok. При первом посещении нажмите "Visit Site" на странице предупреждения ngrok.

## Проблемы и решения

### ❌ ERR_NGROK_3200 - "Tunnel not found" или "Call internal services"

**Причина:** ngrok не может проксировать запросы к localhost без флага `--host-header`

**Решение:**
```powershell
# ПРАВИЛЬНО ✅
ngrok http 8000 --host-header=localhost:8000

# НЕПРАВИЛЬНО ❌
ngrok http 8000
```

Используйте готовый скрипт `.\start_ngrok.bat` который автоматически добавляет нужный флаг.

### 403 Forbidden
Если вы видите ошибку 403:

1. **Убедитесь, что переменная NGROK_DOMAIN установлена**
   - Проверьте, что вы передали домен в батник
   - Перезапустите Django с правильным доменом

2. **Проверьте настройки в Django**
   ```powershell
   cd visitor_system
   poetry run python manage.py shell
   ```
   Затем в shell:
   ```python
   from django.conf import settings
   print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
   print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)
   ```

3. **Очистите куки и кэш браузера**
   - Django может кэшировать настройки CSRF
   - Откройте сайт в режиме инкогнито

4. **Используйте правильный URL**
   - Всегда используйте HTTPS URL от ngrok
   - НЕ используйте localhost:8000 напрямую после настройки ngrok

5. **Перезапустите ngrok с правильным флагом**
   - Остановите ngrok (Ctrl+C)
   - Запустите снова с `--host-header=localhost:8000`

### Ошибка "Invalid HTTP_HOST header"
Если видите эту ошибку:
```
Invalid HTTP_HOST header: 'xxxx.ngrok-free.app'. You may need to add 'xxxx.ngrok-free.app' to ALLOWED_HOSTS.
```

Решение:
1. Убедитесь, что передали домен в `start_with_ngrok.bat`
2. Перезапустите Django с правильным доменом
3. В dev.py уже установлено `ALLOWED_HOSTS = ['*']`, что должно разрешить все домены

### CSRF verification failed
Если видите ошибку CSRF при отправке форм:

1. **Проверьте CSRF_TRUSTED_ORIGINS**
   В `base.py` должно быть:
   ```python
   if DEBUG:
       CSRF_TRUSTED_ORIGINS.extend([
           'https://*.ngrok-free.app',
           'https://*.ngrok.io',
       ])
   ```

2. **Очистите куки**
   - Откройте DevTools (F12)
   - Application → Cookies → удалите все куки для ngrok домена
   - Обновите страницу

3. **Используйте HTTPS**
   - ngrok предоставляет HTTPS URL - используйте его
   - НЕ пытайтесь использовать HTTP

## Альтернативный метод (без батника)

Если батник не работает, запустите вручную:

```powershell
# Терминал 1: ngrok
ngrok http 8000

# Терминал 2: установите переменную и запустите Django
cd visitor_system
$env:NGROK_DOMAIN = "ваш-домен.ngrok-free.app"
$env:DJANGO_SETTINGS_MODULE = "visitor_system.conf.dev"
poetry run python manage.py runserver 0.0.0.0:8000
```

## Проверка логов

Если проблема не решается, проверьте логи Django:
```powershell
# В директории visitor_system
dir logs\visitor_system.log
# Откройте файл и найдите ошибки
```

## Для разработчиков

Текущие настройки в `conf/dev.py`:
- `DEBUG = True`
- `ALLOWED_HOSTS = ['*']` - разрешены все хосты
- `CSRF_COOKIE_SECURE = False` - куки без HTTPS
- `SESSION_COOKIE_SECURE = False` - сессии без HTTPS
- `SECURE_SSL_REDIRECT = False` - нет принудительного редиректа на HTTPS

Текущие настройки в `conf/base.py` для ngrok:
- Автоматически добавляются паттерны `*.ngrok-free.app` и `*.ngrok.io`
- Если установлена `NGROK_DOMAIN`, она добавляется в `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`
- `USE_X_FORWARDED_HOST = True` - для работы за прокси
- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` - для определения HTTPS

## Полезные команды

```powershell
# Проверить, что сервисы запущены
.\check_services_status.bat

# Остановить все сервисы
.\stop_all.bat

# Проверить статус гостя (если нужно)
.\check_guest_status.ps1
```
