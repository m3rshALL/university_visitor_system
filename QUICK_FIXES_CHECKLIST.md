# 🚨 Критические пробелы HikVision - Быстрый чеклист

## ✅ Что УЖЕ исправлено

1. **person_id сохранение в Visit** - `enroll_face_task` теперь сохраняет person_id

---

## 🔴 Что нужно исправить СРОЧНО (блокирует production)

### 1. Race condition между задачами
```python
# СЕЙЧАС (неправильно):
enroll_face_task.apply_async()  # Создаёт person
assign_access_level_task.apply_async()  # Назначает access ПАРАЛЛЕЛЬНО!

# НАДО (правильно):
from celery import chain
chain(
    enroll_face_task.s(task_id),
    assign_access_level_task.s(access_task_id)
).apply_async()
```

### 2. Нет retry при сбоях API
```python
# Добавить в tasks.py:
@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def assign_access_level_task(self, task_id):
    try:
        # код
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 3. auto_close_expired_visits НЕ отзывает доступ
```python
# В visitors/tasks.py, функция auto_close_expired_visits:
# Добавить вызов revoke_access_level_from_person()
```

### 4. Нет cleanup при отмене визита
```python
# Создать signal:
@receiver(post_save, sender=Visit)
def revoke_access_on_cancel(sender, instance, **kwargs):
    if instance.status in ['CANCELLED', 'CHECKED_OUT']:
        if instance.access_granted and not instance.access_revoked:
            revoke_access_task.apply_async([instance.id])
```

### 5. Нет периодической очистки старых person
```python
# Создать новую задачу cleanup_old_persons_task()
# Запускать раз в месяц
```

---

## 🟡 Важные функции (для полной работы)

6. **StudentVisit не поддерживается** - добавить те же поля access_granted/person_id
7. **Нет уведомлений сотруднику** - когда гость прошёл/вышел
8. **Изменение времени визита** - не обновляется в HCP
9. **Отмена визита** - доступ остаётся активным
10. **Нет проверки person** - перед назначением access
11. **Нет rate limiting** - при массовой регистрации

---

## 📊 Улучшения (не критично)

12. Security dashboard (real-time)
13. Prometheus metrics
14. UI для ручного управления
15. Фотофиксация проходов
16. Обработка Face Recognition Failed

---

## 🔧 Оптимизации (можно позже)

17. Cleanup old persons task
18. Защита от дубликатов person
19. Webhook вместо polling
20. Синхронизация с HCP
21. Backup/restore person
22-26. Прочие оптимизации

---

## 📋 План действий (Приоритет 1)

**Сегодня (2-3 часа):**
- [ ] Fix #2: Chain tasks
- [ ] Fix #3: Retry mechanism
- [ ] Fix #4: auto_close + revoke

**Завтра (2 часа):**
- [ ] Fix #5: Cleanup signal
- [ ] Fix #10: Person validity check
- [ ] Тестирование

**После этого система будет готова к production на 100%!**

---

## 🧪 Как проверить исправления

```bash
# 1. Создать тестовый визит
cd visitor_system
poetry run python create_test_visit.py

# 2. Проверить что person_id сохранился
poetry run python manage.py shell
>>> from visitors.models import Visit
>>> v = Visit.objects.last()
>>> v.hikcentral_person_id  # Должен быть не None!

# 3. Проверить мониторинг
poetry run python test_monitoring_task.py

# 4. Проверить автоблокировку (имитация)
poetry run python manage.py shell
>>> v.first_exit_detected = timezone.now()
>>> v.save()
>>> # Запустить monitor_guest_passages_task
>>> # Проверить что access_revoked = True
```

---

**Статус:** 5 критических багов → 1 исправлен ✅, 4 осталось ❌
