# 🔐 Настройка уровней доступа к Dashboards

**Дата:** 14.10.2025  
**Статус:** ✅ **НАСТРОЕНО**

---

## 📊 DASHBOARDS И УРОВНИ ДОСТУПА

### 1. Auto Check-in Dashboard
**URL:** `/visitors/dashboards/auto-checkin/`  
**Permission:** `visitors.view_visit`

**Кто видит:**
- ✅ Все сотрудники с правом просмотра визитов
- ✅ Менеджеры департаментов
- ✅ Администраторы

**Что видит:**
- Статистика автоматических check-in/checkout
- График проходов через турникеты
- Последние автоматические действия
- Топ-10 аномалий

---

### 2. Security Incidents Dashboard
**URL:** `/visitors/dashboards/security-incidents/`  
**Permission:** `visitors.view_securityincident`

**Кто видит:**
- ✅ Администраторы безопасности (Security Admins)
- ✅ Суперпользователи
- ⚠️ НЕ видят обычные сотрудники

**Что видит:**
- Полный список security incidents
- Фильтрация по severity, status, type
- Статистика по типам инцидентов
- Управление инцидентами через админ-панель

---

### 3. HikCentral Dashboard
**URL:** `/visitors/dashboards/hikcentral/`  
**Permission:** `visitors.view_visit`

**Кто видит:**
- ✅ Все сотрудники с правом просмотра визитов
- ✅ IT администраторы
- ✅ Менеджеры

**Что видит:**
- Статус HikCentral серверов
- Статистика интеграции
- Rate limiter status
- Performance metrics

---

## 🎯 НАСТРОЙКА ГРУПП ДОСТУПА

### Вариант 1: Через Django Admin (РЕКОМЕНДУЕТСЯ)

1. Откройте Django Admin: `http://localhost:8000/admin/`
2. Перейдите в **Группы** (`Auth` > `Groups`)
3. Создайте следующие группы:

#### Группа: "Security Admins"
**Права:**
```
✅ visitors | visit | Can view visit
✅ visitors | security incident | Can view security incident
✅ visitors | security incident | Can change security incident
✅ visitors | audit log | Can view audit log
```

**Члены группы:**
- Сотрудники службы безопасности
- Главный охранник
- Менеджер по безопасности

---

#### Группа: "Department Managers"
**Права:**
```
✅ visitors | visit | Can view visit
✅ visitors | visit | Can add visit
✅ visitors | visit | Can change visit
✅ visitors | guest | Can view guest
```

**Члены группы:**
- Руководители департаментов
- HR менеджеры
- Секретари

---

#### Группа: "IT Administrators"
**Права:**
```
✅ visitors | visit | Can view visit
✅ hikvision_integration | hik central server | Can view hik central server
✅ hikvision_integration | hik central server | Can change hik central server
```

**Члены группы:**
- IT специалисты
- Системные администраторы
- DevOps

---

### Вариант 2: Программная настройка

Создайте management command для автоматической настройки групп:

**Файл:** `visitor_system/visitors/management/commands/setup_dashboard_permissions.py`

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Setup dashboard access groups and permissions'
    
    def handle(self, *args, **options):
        # Security Admins Group
        security_group, created = Group.objects.get_or_create(name='Security Admins')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group: Security Admins'))
        
        # Add permissions
        permissions = [
            'visitors.view_visit',
            'visitors.view_securityincident',
            'visitors.change_securityincident',
            'visitors.view_auditlog',
        ]
        
        for perm_str in permissions:
            app_label, codename = perm_str.split('.')
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type__app_label=app_label
                )
                security_group.permissions.add(perm)
                self.stdout.write(f'  Added permission: {perm_str}')
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  Permission not found: {perm_str}')
                )
        
        # Department Managers Group
        managers_group, created = Group.objects.get_or_create(name='Department Managers')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group: Department Managers'))
        
        permissions = [
            'visitors.view_visit',
            'visitors.add_visit',
            'visitors.change_visit',
            'visitors.view_guest',
        ]
        
        for perm_str in permissions:
            app_label, codename = perm_str.split('.')
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type__app_label=app_label
                )
                managers_group.permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        
        # IT Administrators Group
        it_group, created = Group.objects.get_or_create(name='IT Administrators')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group: IT Administrators'))
        
        permissions = [
            'visitors.view_visit',
            'hikvision_integration.view_hikcentralserver',
            'hikvision_integration.change_hikcentralserver',
        ]
        
        for perm_str in permissions:
            app_label, codename = perm_str.split('.')
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type__app_label=app_label
                )
                it_group.permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup dashboard permissions!')
        )
```

**Запуск:**
```bash
cd visitor_system
poetry run python manage.py setup_dashboard_permissions
```

---

## 🔒 ДОПОЛНИТЕЛЬНЫЕ УРОВНИ ЗАЩИТЫ

### 1. IP-based restrictions (опционально)

Ограничьте доступ к Security Incidents Dashboard только с определенных IP:

**Файл:** `visitor_system/visitors/dashboards.py`

```python
from django.http import HttpResponseForbidden

ALLOWED_IPS_FOR_SECURITY = [
    '192.168.1.100',  # Security office
    '192.168.1.101',  # IT department
    '127.0.0.1',      # Localhost
]

@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def security_incidents_dashboard(request):
    # IP-based check
    client_ip = request.META.get('REMOTE_ADDR')
    if client_ip not in ALLOWED_IPS_FOR_SECURITY:
        return HttpResponseForbidden(
            'Access to Security Incidents Dashboard is restricted to authorized IPs only.'
        )
    
    # ... rest of the code ...
```

---

### 2. Time-based restrictions (опционально)

Ограничьте доступ к dashboards только в рабочее время:

```python
from django.utils import timezone

@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def security_incidents_dashboard(request):
    # Time-based check (work hours only)
    now = timezone.now()
    work_start = 8  # 08:00
    work_end = 18   # 18:00
    
    if now.hour < work_start or now.hour >= work_end:
        if not request.user.is_superuser:
            return HttpResponseForbidden(
                'Access to Security Incidents Dashboard is only available during work hours (08:00-18:00).'
            )
    
    # ... rest of the code ...
```

---

### 3. Multi-factor Authentication (опционально)

Требуйте 2FA для доступа к Security Incidents Dashboard:

```python
@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def security_incidents_dashboard(request):
    # Check if user has 2FA enabled
    if hasattr(request.user, 'two_factor_enabled'):
        if not request.user.two_factor_enabled:
            messages.warning(
                request,
                'Two-Factor Authentication is required for Security Dashboard access.'
            )
            return redirect('enable_2fa')
    
    # ... rest of the code ...
```

---

## 📋 CHECKLIST ПО НАСТРОЙКЕ

### Шаг 1: Создать группы
```bash
# В Django Admin
http://localhost:8000/admin/auth/group/

# Или через management command
poetry run python manage.py setup_dashboard_permissions
```

### Шаг 2: Назначить пользователей
```bash
# В Django Admin
http://localhost:8000/admin/auth/user/

# Для каждого пользователя:
1. Открыть пользователя
2. Прокрутить до "Groups"
3. Выбрать нужные группы
4. Сохранить
```

### Шаг 3: Проверить доступ

**Тестовые сценарии:**

1. **Обычный сотрудник:**
   - ✅ Видит Auto Check-in Dashboard
   - ❌ НЕ видит Security Incidents Dashboard
   - ✅ Видит HikCentral Dashboard

2. **Security Admin:**
   - ✅ Видит все 3 dashboards
   - ✅ Может управлять инцидентами

3. **IT Administrator:**
   - ✅ Видит все 3 dashboards
   - ✅ Может управлять HCP серверами

---

## 🎨 ОТОБРАЖЕНИЕ В EMPLOYEE DASHBOARD

В `employee_dashboard.html` уже настроены permissions checks:

```django
<!-- Auto Check-in Dashboard -->
{% if perms.visitors.view_visit %}
<div class="col-md-4 col-lg-3">
    <a href="{% url 'auto_checkin_dashboard' %}" ...>
        Автоматические действия
    </a>
</div>
{% endif %}

<!-- Security Incidents Dashboard -->
{% if perms.visitors.view_securityincident %}
<div class="col-md-4 col-lg-3">
    <a href="{% url 'security_incidents_dashboard' %}" ...>
        Security Incidents
    </a>
</div>
{% endif %}

<!-- HikCentral Dashboard -->
{% if perms.visitors.view_visit %}
<div class="col-md-4 col-lg-3">
    <a href="{% url 'hikcentral_dashboard' %}" ...>
        HikCentral Dashboard
    </a>
</div>
{% endif %}
```

**Результат:**
- Карточки dashboards показываются **только** пользователям с нужными правами
- Неавторизованные пользователи их не видят

---

## 📊 МАТРИЦА ДОСТУПА

| Роль / Dashboard | Auto Check-in | Security Incidents | HikCentral |
|-----------------|---------------|-------------------|------------|
| Обычный сотрудник | ✅ | ❌ | ✅ |
| Department Manager | ✅ | ❌ | ✅ |
| Security Admin | ✅ | ✅ | ✅ |
| IT Administrator | ✅ | ⚠️ (view only) | ✅ |
| Superuser | ✅ | ✅ | ✅ |

---

## 🔐 BEST PRACTICES

1. **Principle of Least Privilege**
   - Давайте минимальные права для выполнения задач
   - Security Incidents - только security team

2. **Regular Audits**
   - Проверяйте права доступа раз в квартал
   - Удаляйте неиспользуемые учетные записи

3. **Logging**
   - Все действия в Security Incidents логируются через AuditLog
   - Мониторинг подозрительной активности

4. **Training**
   - Обучайте сотрудников безопасному использованию dashboards
   - Документируйте процедуры

---

## ✅ ИТОГ

**Текущая конфигурация:**
- ✅ 3 dashboards с разными уровнями доступа
- ✅ Permissions checks в views
- ✅ Условное отображение в Employee Dashboard
- ✅ Готовые группы для назначения

**Для активации:**
1. Создайте группы через Django Admin
2. Назначьте пользователей в группы
3. Проверьте доступ

**Безопасность:** 🟢 Высокая

---

**Автор:** AI Assistant  
**Дата:** 14.10.2025

