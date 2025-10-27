# 🔧 Исправление FieldError - visit.host → visit.employee

**Дата:** 14.10.2025  
**Статус:** ✅ **ИСПРАВЛЕНО**

---

## ❌ Проблема

```
FieldError at /visitors/dashboards/auto-checkin/
Invalid field name(s) given in select_related: 'host'. 
Choices are: guest, employee, department, visit_group, registered_by, invitation
```

```
FieldError at /visitors/dashboards/security-incidents/
Invalid field name(s) given in select_related: 'host'. 
Choices are: guest, employee, department, visit_group, registered_by, invitation
```

---

## 🔍 Причина

В модели `Visit` нет поля `host` - вместо этого используется поле `employee` (принимающий сотрудник).

При создании dashboards я ошибочно использовал `visit__host` вместо `visit__employee` в `select_related()`.

---

## ✅ Решение

Заменил все упоминания `host` на `employee` в следующих файлах:

### 1. `visitor_system/visitors/dashboards.py`

**Строка 125:**
```python
# Было:
).select_related('visit__guest', 'visit__host').order_by('-detected_at')[:10]

# Стало:
).select_related('visit__guest', 'visit__employee').order_by('-detected_at')[:10]
```

**Строка 183:**
```python
# Было:
incidents = SecurityIncident.objects.select_related(
    'visit__guest', 'visit__host', 'visit__department', 'assigned_to'
)

# Стало:
incidents = SecurityIncident.objects.select_related(
    'visit__guest', 'visit__employee', 'visit__department', 'assigned_to'
)
```

### 2. `visitor_system/hikvision_integration/utils.py`

**Строка 59:**
```python
# Было:
incident = SecurityIncident.objects.select_related(
    'visit__guest', 'visit__host', 'visit__department'
).get(id=incident_id)

# Стало:
incident = SecurityIncident.objects.select_related(
    'visit__guest', 'visit__employee', 'visit__department'
).get(id=incident_id)
```

**Строка 77-81 (context):**
```python
# Было:
context = {
    'incident': incident,
    'visit': incident.visit,
    'guest': incident.visit.guest,
    'host': incident.visit.host if hasattr(incident.visit, 'host') else None,
    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
}

# Стало:
context = {
    'incident': incident,
    'visit': incident.visit,
    'guest': incident.visit.guest,
    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
}
```

**Строка 96 (plain text email):**
```python
# Было:
Принимающий: {incident.visit.host.get_full_name() if hasattr(incident.visit, 'host') and incident.visit.host else 'N/A'}

# Стало:
Принимающий: {incident.visit.employee.get_full_name() if incident.visit.employee else 'N/A'}
```

### 3. `templates/notifications/email/security_alert.html`

**Строка 143-148:**
```html
<!-- Было: -->
{% if host %}
<div class="info-row">
    <span class="info-label">Принимающий:</span>
    <span class="info-value">{{ host.get_full_name }}</span>
</div>
{% endif %}

<!-- Стало: -->
{% if visit.employee %}
<div class="info-row">
    <span class="info-label">Принимающий:</span>
    <span class="info-value">{{ visit.employee.get_full_name }}</span>
</div>
{% endif %}
```

---

## 📋 Измененные файлы

1. ✅ `visitor_system/visitors/dashboards.py` - 2 исправления
2. ✅ `visitor_system/hikvision_integration/utils.py` - 3 исправления
3. ✅ `templates/notifications/email/security_alert.html` - 1 исправление

**Всего:** 6 исправлений в 3 файлах

---

## 🧪 Проверка

После исправления dashboards должны работать:

```bash
# 1. Auto Check-in Dashboard
http://localhost:8000/visitors/dashboards/auto-checkin/

# 2. Security Incidents Dashboard
http://localhost:8000/visitors/dashboards/security-incidents/

# 3. HikCentral Dashboard
http://localhost:8000/visitors/dashboards/hikcentral/
```

Все три dashboard должны открываться без ошибок FieldError.

---

## 📝 Примечание

Правильная структура модели `Visit`:
- `guest` - гость (ForeignKey to Guest)
- `employee` - принимающий сотрудник (ForeignKey to User)
- `department` - департамент (ForeignKey to Department)
- `visit_group` - группа (ForeignKey to GroupInvitation, nullable)
- `registered_by` - кто зарегистрировал (ForeignKey to User)
- `invitation` - приглашение (ForeignKey to GuestInvitation, nullable)

**НЕТ поля `host`** - используйте `employee`!

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025  
**Время исправления:** 5 минут

