# Исправление ошибок HikCentral (Код 64)

## Обнаруженные проблемы

### ✅ Проблема 1: NameError - ИСПРАВЛЕНО
**Описание:** Функции `visitor_auth_reapplication` и `visitor_out` не были определены в `services.py`

**Решение:** Удалены вызовы несуществующих функций из `tasks.py`. Reapplication и revoke теперь выполняются в отдельных тасках:
- `assign_access_level_task` - для назначения доступа
- `revoke_access_level_task` - для отзыва доступа

---

### ❌ Проблема 2: Код 64 "User authentication failed" - ТРЕБУЕТ ДЕЙСТВИЙ

**Причина:** Integration Key слишком короткий (8 символов вместо 20-32)

**Текущие значения:**
```
Integration Key:    8 символов  [WARNING: подозрительно короткий!]
Integration Secret: 20 символов [OK]
```

## Как исправить ошибку 64

### Шаг 1: Получите правильные credentials в HikCentral

1. Откройте **HikCentral Professional** web-интерфейс
2. Перейдите: **System → Security → Integration Partner**
3. Найдите или создайте Integration Partner для вашего приложения
4. **Скопируйте:**
   - **AppKey** (Integration Partner Key) - обычно 20-32 символа
   - **AppSecret** (Integration Partner Secret) - обычно 32-64 символа

### Шаг 2: Проверьте права доступа

В настройках Integration Partner убедитесь, что включены:
- ✅ **Status: Enabled**
- ✅ **Access Control Management** (управление доступом)
- ✅ **Person Management** (управление персонами)
- ✅ **Face Recognition** (распознавание лиц)
- ✅ **Visitor Management** (управление посетителями)

### Шаг 3: Обновите credentials в Django Admin

1. Откройте Django Admin: **http://localhost:8000/admin/**
2. Перейдите: **Hikvision Integration → Серверы HikCentral**
3. Откройте сервер **"HikCentral Professional"**
4. Обновите поля:
   - **Integration Partner Key** = AppKey из HikCentral
   - **Integration Partner Secret** = AppSecret из HikCentral
5. Убедитесь что **Включен** = ✅ (checked)
6. Нажмите **Сохранить**

### Шаг 4: Перезапустите Celery worker

```bash
# Остановите текущий worker (Ctrl+C)
# Затем запустите снова:
start_celery.bat
```

### Шаг 5: Проверьте credentials

Запустите скрипт проверки:
```bash
check_hikcentral_credentials.bat
```

Или вручную:
```bash
poetry run python check_hikcentral_credentials.py
```

Вывод должен показать `[SUCCESS] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!`

---

## Проверка работы

После исправления попробуйте создать нового гостя:

1. Откройте форму создания приглашения
2. Заполните данные гостя
3. Загрузите фото
4. Создайте приглашение

**Проверьте логи Celery:**
- ✅ Не должно быть `code: '64'`
- ✅ Должно быть `code: '0'` (успех)
- ✅ Не должно быть ошибок `User authentication failed`

---

## Дополнительная диагностика

### Если код 64 все ещё появляется:

1. **Проверьте URL сервера**
   - Формат: `https://IP:PORT` (например, `https://10.1.18.29:444`)
   - Проверьте доступность через браузер

2. **Проверьте сертификаты**
   - HikCentral использует самоподписанные сертификаты
   - В коде уже установлено `verify=False`

3. **Проверьте настройки времени**
   - Подпись Artemis API чувствительна к времени
   - Убедитесь, что время на сервере Django синхронизировано с HikCentral

4. **Включите отладку подписи**
   
   В `visitor_system/settings.py` добавьте:
   ```python
   HIKCENTRAL_DEBUG_SIGN = True
   ```
   
   Это выведет в логи строку для подписи и заголовки запроса

5. **Проверьте версию HikCentral**
   - Требуется HikCentral Professional v2.0+
   - Artemis API может отличаться в разных версиях

---

## Контакты для поддержки

Если проблема сохраняется:
1. Сохраните логи Celery с `HIKCENTRAL_DEBUG_SIGN = True`
2. Сделайте скриншот настроек Integration Partner в HikCentral
3. Запустите `check_hikcentral_credentials.bat` и сохраните вывод
4. Обратитесь к администратору HikCentral

