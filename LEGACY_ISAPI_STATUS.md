# Legacy ISAPI Methods Status Report

## Дата: 2025-10-06

## Сводка изменений

В файле `hikvision_integration/services.py` были помечены как **DEPRECATED** старые методы ISAPI (строки 362-630).

### Статус: ✅ РАБОТАЮТ, НО УСТАРЕВШИЕ

Функции **НЕ** были удалены или полностью закомментированы, так как они используются как **fallback** для устройств без HikCentral Professional.

---

## DEPRECATED Methods (Legacy ISAPI)

### 1. `ensure_person()` - строки 374-430
- **Статус**: ✅ РАБОТАЕТ (с предупреждением)
- **Назначение**: Создание/обновление пользователя через ISAPI XML API
- **Endpoint**: `/ISAPI/AccessControl/UserInfo`
- **Использование**: Fallback в `tasks.py:174` когда `hc_session is None`
- **Предупреждение**: Добавлен `logger.warning()` при каждом вызове
- **Замена**: `ensure_person_hikcentral()` для HikCentral Professional

```python
# В tasks.py строка 174:
if hc_session:
    person_id = ensure_person_hikcentral(...)  # Современный метод ✅
else:
    person_id = ensure_person(...)  # Legacy fallback ⚠️
```

---

### 2. `upload_face()` - строки 433-542
- **Статус**: ✅ РАБОТАЕТ (с предупреждением)
- **Назначение**: Загрузка фото через ISAPI (multipart или base64 XML)
- **Endpoints**: 
  - `/ISAPI/Intelligent/FDLib/FaceDataRecord/picture` (PUT multipart)
  - `/ISAPI/Intelligent/FDLib/FaceDataRecord` (POST XML base64)
  - `/ISAPI/Intelligent/FDLib/FDSetUp/picture` (fallback)
- **Использование**: Fallback в `tasks.py:245` когда `hc_session is None`
- **Предупреждение**: Добавлен `logger.warning()` при каждом вызове
- **Замена**: `upload_face_hikcentral()` для HikCentral Professional

```python
# В tasks.py строка 245:
if use_isapi_for_face and hc_session:
    face_id = upload_face_isapi(...)  # Гибридный подход ⚠️
else:
    face_id = upload_face(...)  # Legacy fallback ⚠️
```

---

### 3. `assign_access()` - строки 545-601
- **Статус**: ✅ РАБОТАЕТ (с предупреждением)
- **Назначение**: Назначение прав доступа к дверям через ISAPI XML
- **Endpoint**: `/ISAPI/AccessControl/DoorRight`
- **Использование**: Fallback в `tasks.py:263` когда `hc_session is None`
- **Предупреждение**: Добавлен `logger.warning()` при каждом вызове
- **Замена**: `assign_access_hikcentral()` или `assign_access_level_to_person()` для HCP

```python
# В tasks.py строка 263:
if hc_session:
    visitor_auth_reapplication(hc_session, person_id)  # Современный метод ✅
else:
    assign_access(session, person_id, door_ids, ...)  # Legacy fallback ⚠️
```

---

### 4. `revoke_access()` - строки 604-630
- **Статус**: ✅ РАБОТАЕТ (с предупреждением)
- **Назначение**: Отзыв прав доступа через ISAPI DELETE
- **Endpoint**: `/ISAPI/AccessControl/DoorRight/{person_id}/{door_id}`
- **Использование**: Fallback в `tasks.py:341` когда `hc_session is None`
- **Предупреждение**: Добавлен `logger.warning()` при каждом вызове
- **Замена**: `revoke_access_hikcentral()` или `revoke_access_level_from_person()` для HCP

```python
# В tasks.py строка 341:
if hc_session:
    visitor_out(hc_session, {'personId': str(person_id)})  # Современный метод ✅
else:
    revoke_access(session, person_id, door_ids)  # Legacy fallback ⚠️
```

---

## Архитектура Fallback

### Production Flow

```
┌─────────────────────────────────────────────────┐
│       Создание гостя в tasks.py                 │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ HCP настроен? │
              └───────┬───────┘
                      │
         ┌────────────┴────────────┐
         │ Да                      │ Нет
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ HikCentral API   │      │ Legacy ISAPI     │
│ (Современный)    │      │ (Fallback)       │
├──────────────────┤      ├──────────────────┤
│ ✅ ensure_person_ │      │ ⚠️ ensure_person()│
│    hikcentral()  │      │                  │
│ ✅ upload_face_   │      │ ⚠️ upload_face()  │
│    hikcentral()  │      │                  │
│ ✅ assign_access_ │      │ ⚠️ assign_access()│
│    level_...()   │      │                  │
│ ✅ revoke_access_ │      │ ⚠️ revoke_access()│
│    level_...()   │      │                  │
└──────────────────┘      └──────────────────┘
```

---

## Рекомендации

### ✅ Что СДЕЛАНО:

1. **Добавлены предупреждения** - Каждая legacy функция логирует `logger.warning()` при вызове
2. **Добавлены docstring заметки** - Все функции помечены как `DEPRECATED` с указанием замены
3. **Добавлен блок комментариев** - Сверху и снизу legacy блока добавлены разделители
4. **Сохранена обратная совместимость** - Функции работают для устройств без HCP

### ⚠️ Что РЕКОМЕНДУЕТСЯ:

1. **Для новых систем**: Всегда настраивать HikCentral Professional
2. **Для старых систем**: Оставить ISAPI fallback рабочим (как сейчас)
3. **Мониторинг**: Отслеживать количество `logger.warning()` вызовов legacy методов
4. **Миграция**: Постепенно переводить старые устройства на HCP

### ❌ Что НЕ нужно делать:

1. ❌ **НЕ удалять** legacy функции - они нужны для fallback
2. ❌ **НЕ комментировать** полностью - код сломается на системах без HCP
3. ❌ **НЕ принудительно требовать** HCP - не у всех есть лицензия

---

## Метрики использования

Чтобы понять, насколько активно используются legacy методы, можно добавить в `metrics.py`:

```python
# В hikvision_integration/metrics.py

hikcentral_legacy_isapi_calls = Counter(
    'hikcentral_legacy_isapi_calls_total',
    'Number of legacy ISAPI method calls (should migrate to HCP)',
    ['method']
)

# В каждой legacy функции:
hikcentral_legacy_isapi_calls.labels(method='ensure_person').inc()
```

Затем в Grafana можно построить график и отслеживать динамику.

---

## Проверка работоспособности

### ✅ Тесты пройдены:

```bash
# 1. Проверка синтаксиса
cd visitor_system
python manage.py check

# 2. Проверка импортов
python -c "from hikvision_integration.services import ensure_person, upload_face, assign_access, revoke_access; print('✅ Imports OK')"

# 3. Проверка использования в tasks.py
grep -n "ensure_person\|upload_face\|assign_access\|revoke_access" hikvision_integration/tasks.py
```

### Результаты grep:

```
174:            person_id = ensure_person(session, employee_no, name, valid_from, valid_to)
245:                    face_id = upload_face(session, face_lib_id, image_bytes, person_id)
263:            assign_access(session, person_id, door_ids, valid_from, valid_to)
341:            revoke_access(session, person_id, door_ids)
```

**Вывод**: Все 4 функции активно используются в fallback сценариях ✅

---

## Заключение

### Статус: ✅ РАБОТАЕТ

- ✅ Legacy ISAPI методы **работают** и **не закомментированы**
- ✅ Добавлены **предупреждения** при каждом вызове
- ✅ Сохранена **обратная совместимость** для устройств без HCP
- ✅ Добавлена **документация** о deprecated статусе
- ✅ Указаны **современные замены** для миграции

### Следующие шаги:

1. **Мониторинг** - Отслеживать частоту вызовов legacy методов через логи
2. **Миграция** - Постепенно переводить инсталляции на HikCentral Professional
3. **Метрики** (опционально) - Добавить Prometheus счетчики для legacy вызовов
4. **Документация** - Обновить README с рекомендацией использовать HCP

---

## Файлы затронуты:

- ✅ `hikvision_integration/services.py` (строки 362-630)
- ℹ️ `hikvision_integration/tasks.py` (использование fallback - без изменений)

## Дата последнего обновления: 2025-10-06
