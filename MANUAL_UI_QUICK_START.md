# Manual UI - Quick Start Guide

## 🎯 Суть в одной картинке

```
ПОЛЬЗОВАТЕЛЬ                  DJANGO                    CELERY                    HIKCENTRAL
    │                           │                         │                          │
    │  1. Нажимает кнопку       │                         │                          │
    │  "Заблокировать"          │                         │                          │
    ├──────────────────────────>│                         │                          │
    │                           │                         │                          │
    │                           │  2. manual_revoke_      │                          │
    │                           │     access(request)     │                          │
    │                           │  - Проверка прав        │                          │
    │                           │  - Валидация статуса    │                          │
    │                           │                         │                          │
    │                           │  3. Запуск task         │                          │
    │                           ├────────────────────────>│                          │
    │                           │                         │                          │
    │                           │                         │  4. revoke_access_       │
    │                           │                         │     level_task()         │
    │                           │                         │                          │
    │                           │                         │  5. API вызов            │
    │                           │                         ├─────────────────────────>│
    │                           │                         │  POST /acs/v1/privilege/ │
    │                           │                         │  group/single/deletePersons
    │                           │                         │                          │
    │                           │                         │  6. Результат            │
    │                           │                         │<─────────────────────────┤
    │                           │                         │  {"code":"0","msg":"ok"} │
    │                           │                         │                          │
    │                           │  7. Обновление Visit    │                          │
    │                           │<────────────────────────┤                          │
    │                           │  access_revoked=True    │                          │
    │                           │                         │                          │
    │  8. Сообщение             │                         │                          │
    │  "✅ Доступ заблокирован" │                         │                          │
    │<──────────────────────────┤                         │                          │
    │                           │                         │                          │
```

---

## 🔧 Минимальная реализация (20 минут)

### Файл 1: `templates/visitors/visit_detail.html`

**После строки 160 добавить:**

```django-html
{% if visit.hikcentral_person_id and visit.access_granted and not visit.access_revoked %}
<form method="post" action="{% url 'manual_revoke_access' visit.id %}" 
      onsubmit="return confirm('Заблокировать доступ?');">
    {% csrf_token %}
    <input type="hidden" name="reason" value="Manual UI revoke">
    <button type="submit" class="btn btn-danger mt-2">
        🚫 Заблокировать доступ
    </button>
</form>
{% endif %}
```

### Файл 2: `visitors/views.py`

**В конец файла:**

```python
@login_required
@require_POST
def manual_revoke_access(request, visit_id):
    """Простая блокировка доступа."""
    if not request.user.is_staff:
        messages.error(request, "Нет прав")
        return redirect('visit_detail', visit_id=visit_id)
    
    visit = get_object_or_404(Visit, pk=visit_id)
    
    if not visit.access_granted or visit.access_revoked:
        messages.warning(request, "Доступ уже отозван")
        return redirect('visit_detail', visit_id=visit_id)
    
    try:
        from hikvision_integration.tasks import revoke_access_level_task
        revoke_access_level_task.delay(visit.id)
        
        visit.access_revoked = True
        visit.save()
        
        messages.success(request, "✅ Доступ заблокирован")
    except Exception as e:
        messages.error(request, f"❌ Ошибка: {e}")
    
    return redirect('visit_detail', visit_id=visit_id)
```

### Файл 3: `visitors/urls.py`

```python
path('visit/<int:visit_id>/manual/revoke/', 
     views.manual_revoke_access, 
     name='manual_revoke_access'),
```

**ВСЁ!** Теперь на странице визита появится кнопка блокировки.

---

## 🚀 Полная версия (4 часа)

См. файл `MANUAL_UI_IMPLEMENTATION_GUIDE.md` - там 1000+ строк кода с:

- ✅ 4 типа действий (блокировка, продление, восстановление, удаление)
- ✅ Bootstrap модальные окна
- ✅ htmx для обновления без перезагрузки
- ✅ Права доступа по группам
- ✅ Audit trail
- ✅ История действий

---

## 🎨 Визуальный результат

### До реализации:
```
┌─────────────────────────────────────┐
│ Детали визита №123                  │
├─────────────────────────────────────┤
│ Информация о госте...               │
│ Информация о визите...              │
│                                     │
│ [← Назад]  [Гость вышел]           │
└─────────────────────────────────────┘
```

### После реализации:
```
┌─────────────────────────────────────┐
│ Детали визита №123                  │
├─────────────────────────────────────┤
│ Информация о госте...               │
│ Информация о визите...              │
│                                     │
│ ┌─ 🔒 Управление доступом ────────┐│
│ │ HCP ID: 12345678                ││
│ │ Статус: ✅ АКТИВЕН до 18:00     ││
│ │                                  ││
│ │ [🚫 Заблокировать] [⏱️ Продлить]││
│ │ [🔄 Обновить]                    ││
│ └──────────────────────────────────┘│
│                                     │
│ [← Назад]  [Гость вышел]           │
└─────────────────────────────────────┘
```

---

## ❓ FAQ

### Q: Зачем нужно Manual UI, если есть автоматика?

**A:** Реальные сценарии:

- 🕐 Встреча затянулась → продлить на 2 часа
- ⚠️ Гость нарушил правила → немедленно заблокировать
- 🔧 Технический сбой → вручную открыть доступ
- 🚨 Эвакуация → массово заблокировать все входы

### Q: Кто может управлять доступом?

**A:** Настраивается в коде:

```python
# Базовая проверка
if not request.user.is_staff:
    return forbidden

# Проверка по группам
if request.user.groups.filter(name__in=['Security', 'Reception']).exists():
    allow()
```

### Q: Это безопасно?

**A:** Да, с условиями:

- ✅ Все действия логируются в AuditLog
- ✅ Требуется подтверждение для опасных действий
- ✅ Права доступа проверяются на backend
- ✅ CSRF protection включён

### Q: Можно массово управлять гостями?

**A:** Да, расширение:

```python
# Bulk extend - продлить 10 гостей на 2 часа
def bulk_extend_access(request):
    visit_ids = request.POST.getlist('visit_ids')
    for vid in visit_ids:
        update_person_validity_task.delay(vid, hours=2)
```

### Q: Как посмотреть историю действий?

**A:** Запрос к AuditLog:

```python
logs = AuditLog.objects.filter(
    model='Visit',
    object_id=str(visit_id),
    action__in=['MANUAL_REVOKE', 'MANUAL_EXTEND']
).order_by('-created_at')
```

---

## 📊 Метрики

После внедрения можно отследить:

```sql
-- Топ пользователей Manual UI
SELECT 
    actor__username,
    COUNT(*) as actions_count
FROM visitors_auditlog
WHERE action LIKE 'MANUAL_%'
GROUP BY actor__username
ORDER BY actions_count DESC
LIMIT 10;

-- Самые частые действия
SELECT 
    action,
    COUNT(*) as count
FROM visitors_auditlog
WHERE action LIKE 'MANUAL_%'
GROUP BY action;

-- Гости с частыми продлениями (проблемные визиты?)
SELECT 
    v.id,
    g.full_name,
    COUNT(*) as extend_count
FROM visitors_auditlog a
JOIN visitors_visit v ON a.object_id = CAST(v.id AS TEXT)
JOIN visitors_guest g ON v.guest_id = g.id
WHERE a.action = 'MANUAL_EXTEND'
GROUP BY v.id, g.full_name
HAVING COUNT(*) > 2
ORDER BY extend_count DESC;
```

---

## 🎯 Следующие шаги

### Этап 1: Минимум (20 мин)
- [ ] Добавить кнопку "Заблокировать" в visit_detail.html
- [ ] Создать view `manual_revoke_access()`
- [ ] Добавить URL route
- [ ] Протестировать

### Этап 2: Расширение (2 часа)
- [ ] Добавить кнопку "Продлить"
- [ ] Модальное окно с выбором часов
- [ ] View `manual_extend_access()`
- [ ] Протестировать

### Этап 3: Полная версия (1 час)
- [ ] Кнопка "Обновить" (htmx)
- [ ] Кнопка "Удалить Person" (опасная зона)
- [ ] История действий на странице
- [ ] Права доступа по группам

### Этап 4: Опционально
- [ ] Bulk операции (массовое продление)
- [ ] Экспорт истории действий
- [ ] Grafana dashboard с метриками
- [ ] Email уведомления при блокировке

---

## 🔗 Связанные файлы

- 📄 `MANUAL_UI_IMPLEMENTATION_GUIDE.md` - Полное руководство (1000+ строк)
- 📄 `SYSTEM_GAPS_AND_ROADMAP.md` - Общий roadmap
- 📄 `HIKVISION_GAPS_ANALYSIS.md` - Анализ пробелов

---

## 💡 Совет

Начните с **минимальной реализации** (20 минут), протестируйте, получите feedback от пользователей, затем расширяйте функционал по мере необходимости.

**Принцип:** Лучше простая рабочая кнопка сейчас, чем идеальная панель через месяц! 🚀
