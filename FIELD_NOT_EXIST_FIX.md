# Исправление: FieldDoesNotExist - expected_exit_time

**Дата:** 14.10.2025  
**Ошибка:** `django.core.exceptions.FieldDoesNotExist: Visit has no field named 'expected_exit_time'`

---

## ❌ Проблема

Код использовал несуществующее поле `expected_exit_time` в модели `Visit`.

**Файлы с ошибкой:**
1. `visitor_system/hikvision_integration/tasks.py` (строка 1127)
2. `visitor_system/visitors/signals.py` (строки 215-216, 229)
3. `visitor_system/test/test_full_guest_flow.py` (строка 60)

---

## ✅ Исправления

### 1. tasks.py - update_person_validity_task

**Было:**
```python
if visit.expected_exit_time:
    end_datetime = visit.expected_exit_time  # ← Поле не существует!
else:
    # Fallback
    ...
```

**Стало:**
```python
# Используем HIKCENTRAL_ACCESS_END_TIME из настроек
access_end_time_str = getattr(settings, 'HIKCENTRAL_ACCESS_END_TIME', '22:00')
access_end_time = datetime.strptime(access_end_time_str, '%H:%M').time()
end_datetime = timezone.make_aware(datetime.combine(now.date(), access_end_time))
```

**Также добавлено:**
- Замена `_get_hikcentral_session()` на `_get_hikcentral_server()`
- Context manager для автоматического закрытия сессии

---

### 2. signals.py - update_hikcentral_validity_on_time_change

**Было:**
```python
@receiver(post_save, sender=Visit)
def update_hikcentral_validity_on_time_change(...):
    old_instance = Visit.objects.only('expected_exit_time').get(pk=instance.pk)
    if old_instance.expected_exit_time == instance.expected_exit_time:
        ...
```

**Стало:**
```python
# ОТКЛЮЧЕНО: Поле expected_exit_time не существует в модели Visit
# @receiver(post_save, sender=Visit)
def update_hikcentral_validity_on_time_change(...):
    """
    ОТКЛЮЧЕНО: Обновление validity в HikCentral при изменении времени визита.
    
    Причина: Поле expected_exit_time не существует в модели Visit.
    Задача update_person_validity_task использует HIKCENTRAL_ACCESS_END_TIME из settings.
    """
    pass
```

**Решение:** Сигнал отключен, так как поле не существует.

---

### 3. test_full_guest_flow.py

**Было:**
```python
visit = Visit.objects.create(
    ...
    expected_exit_time=timezone.now() + timezone.timedelta(hours=2),  # ← Поле не существует!
    ...
)
```

**Стало:**
```python
visit = Visit.objects.create(
    ...
    # expected_exit_time удалено
    ...
)
```

---

## 📋 Модель Visit - Существующие поля

Для справки, в модели `Visit` есть:
- ✅ `expected_entry_time` - планируемое время входа
- ✅ `entry_time` - фактическое время входа
- ✅ `exit_time` - время выхода
- ❌ `expected_exit_time` - **НЕ СУЩЕСТВУЕТ**

---

## 🎯 Итог

**Исправлено файлов:** 3

1. ✅ `tasks.py` - убрана проверка несуществующего поля
2. ✅ `signals.py` - отключен сигнал
3. ✅ `test_full_guest_flow.py` - убрано поле из теста

**Статус:** ✅ **Ошибка полностью исправлена**

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025

