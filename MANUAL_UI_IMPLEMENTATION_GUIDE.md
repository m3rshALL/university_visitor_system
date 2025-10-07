# Manual UI Implementation Guide

## 📋 Что такое Manual UI?

**Manual UI** - это интерфейс для ручного управления доступом гостей в HikCentral без привязки к автоматическим событиям (вход/выход).

### Зачем это нужно?

**Реальные сценарии:**

1. **Продление доступа** - Встреча затянулась, нужно продлить доступ гостя на 2 часа
2. **Блокировка доступа** - Гость нарушил правила, нужно немедленно заблокировать
3. **Ручная выдача доступа** - Технический сбой, секьюрити вручную открывает доступ
4. **Изменение зон доступа** - Переместить гостя в другое здание/этаж
5. **Экстренные ситуации** - Эвакуация, нужно заблокировать все входы

---

## 🎯 Текущая ситуация

### ✅ Что уже есть:

1. **visit_detail.html** - Страница деталей визита
2. **Кнопка "Гость вышел"** - Ручная отметка выхода (строка 160)
3. **Backend функция** `mark_guest_exit_view()` - Обработка выхода (views.py:737)
4. **HikCentral API** - Функции для управления доступом в services.py:
   - `assign_access_level_to_person()` - Назначение группы доступа
   - `revoke_access_level_from_person()` - Отзыв группы доступа
   - `update_person_validity_task()` - Обновление периода validity

### ❌ Чего не хватает:

1. **Кнопки управления доступом** на странице visit_detail.html
2. **Backend views** для обработки ручных действий
3. **URL routes** для новых действий
4. **AJAX/htmx endpoints** для обновления без перезагрузки
5. **Права доступа** - кто может управлять (только админ? reception?)

---

## 🏗️ Архитектура Manual UI

```
┌─────────────────────────────────────────────────────────────┐
│                     visit_detail.html                       │
│  (Страница детальной информации о визите)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Информация о госте]  |  [Информация о визите]           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🔒 Manual Access Control Panel                      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                        │  │
│  │  Статус доступа: ✅ АКТИВЕН (до 18:00)               │  │
│  │  HikCentral ID: 12345678                              │  │
│  │                                                        │  │
│  │  Действия:                                            │  │
│  │  ┌───────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ 🚫 Заблокиро- │  │ ⏱️ Продлить  │  │ 🔄 Обновить│ │  │
│  │  │    вать       │  │   доступ     │  │   период   │ │  │
│  │  └───────────────┘  └──────────────┘  └────────────┘ │  │
│  │                                                        │  │
│  │  ⚠️ Опасная зона:                                     │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │ 🗑️ Удалить Person из HikCentral                  │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  [История действий]                                         │
│  • 14:30 - Доступ выдан (auto)                             │
│  • 15:45 - Продлен до 18:00 (admin: ivanov)               │
│  • 16:20 - Заблокирован (security: petrov)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend Views (views.py)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  manual_revoke_access(request, visit_id)                   │
│  ├─ Проверка прав (is_staff or is_security)                │
│  ├─ Проверка статуса визита                                │
│  └─ Вызов: revoke_access_level_task.delay(visit_id)        │
│                                                             │
│  manual_extend_access(request, visit_id)                   │
│  ├─ Форма: сколько часов продлить? (1-24h)                │
│  ├─ Вычисление: new_exit_time = old + delta                │
│  └─ Вызов: update_person_validity_task.delay(...)          │
│                                                             │
│  manual_refresh_access(request, visit_id)                  │
│  ├─ Синхронизация: Visit ↔ HikCentral                     │
│  ├─ Получение: get_person_hikcentral(person_id)            │
│  └─ Обновление: Visit.access_granted, expected_exit_time   │
│                                                             │
│  manual_delete_person_hcp(request, visit_id)               │
│  ├─ Подтверждение: "Вы уверены?"                          │
│  ├─ Отзыв доступа                                          │
│  └─ Удаление: delete_person_hikcentral(person_id)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Celery Tasks (tasks.py)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  revoke_access_level_task(visit_id)                        │
│  ├─ Получение: Visit.hikcentral_person_id                  │
│  ├─ API: revoke_access_level_from_person(...)              │
│  ├─ Обновление: Visit.access_revoked = True                │
│  └─ Audit: "Manual revoke by user X"                       │
│                                                             │
│  update_person_validity_task(visit_id, new_exit_time)      │
│  ├─ API: ensure_person_hikcentral(..., valid_to=...)       │
│  ├─ Обновление: Visit.expected_exit_time                   │
│  └─ Audit: "Extended by user X"                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│           HikCentral API (services.py)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  revoke_access_level_from_person(session, person_id, ...)  │
│  assign_access_level_to_person(session, person_id, ...)    │
│  update_person_validity(session, person_id, valid_to, ...) │
│  delete_person_hikcentral(session, person_id)               │
│  get_person_hikcentral(session, person_id)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Пошаговая реализация

### Шаг 1: Добавление UI элементов в visit_detail.html

**Где:** `templates/visitors/visit_detail.html`

**Что добавить:** Панель управления доступом после карточек с информацией

```django-html
<!-- После строки 160 (после кнопки "Гость вышел") -->

{% if visit.hikcentral_person_id %}
<div class="row mt-3">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                        <rect x="5" y="11" width="14" height="10" rx="2"/>
                        <circle cx="12" cy="16" r="1"/>
                        <path d="M8 11v-4a4 4 0 0 1 8 0v4"/>
                    </svg>
                    Ручное управление доступом HikCentral
                </h3>
            </div>
            <div class="card-body">
                <!-- Статус доступа -->
                <div class="mb-3">
                    <div class="row">
                        <div class="col-md-6">
                            <strong>HikCentral Person ID:</strong> 
                            <code>{{ visit.hikcentral_person_id }}</code>
                        </div>
                        <div class="col-md-6">
                            <strong>Статус доступа:</strong>
                            {% if visit.access_granted and not visit.access_revoked %}
                                <span class="badge bg-success">✅ АКТИВЕН</span>
                            {% elif visit.access_revoked %}
                                <span class="badge bg-danger">🚫 ОТОЗВАН</span>
                            {% else %}
                                <span class="badge bg-warning">⏳ НЕ ВЫДАН</span>
                            {% endif %}
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-md-6">
                            <strong>Период доступа:</strong>
                            {% if visit.expected_entry_time and visit.expected_exit_time %}
                                {{ visit.expected_entry_time|date:"Y-m-d H:i" }} → 
                                {{ visit.expected_exit_time|date:"Y-m-d H:i" }}
                            {% else %}
                                <span class="text-muted">Не указан</span>
                            {% endif %}
                        </div>
                        <div class="col-md-6">
                            <strong>Первый проход:</strong>
                            {% if visit.first_entry_detected %}
                                {{ visit.first_entry_detected|date:"Y-m-d H:i:s" }}
                            {% else %}
                                <span class="text-muted">Не зафиксирован</span>
                            {% endif %}
                        </div>
                    </div>
                </div>

                <!-- Кнопки действий -->
                <div class="btn-group" role="group">
                    <!-- 1. Заблокировать доступ -->
                    {% if visit.access_granted and not visit.access_revoked %}
                    <button type="button" 
                            class="btn btn-danger" 
                            data-bs-toggle="modal" 
                            data-bs-target="#revokeAccessModal">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <circle cx="12" cy="12" r="9"/>
                            <path d="M5.7 5.7l12.6 12.6"/>
                        </svg>
                        Заблокировать доступ
                    </button>
                    {% endif %}

                    <!-- 2. Продлить доступ -->
                    {% if visit.access_granted and not visit.access_revoked %}
                    <button type="button" 
                            class="btn btn-warning" 
                            data-bs-toggle="modal" 
                            data-bs-target="#extendAccessModal">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <circle cx="12" cy="12" r="9"/>
                            <polyline points="12 7 12 12 15 15"/>
                        </svg>
                        Продлить доступ
                    </button>
                    {% endif %}

                    <!-- 3. Восстановить доступ -->
                    {% if visit.access_revoked %}
                    <button type="button" 
                            class="btn btn-success" 
                            data-bs-toggle="modal" 
                            data-bs-target="#restoreAccessModal">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M9 11l3 3l8 -8"/>
                            <path d="M20 12v6a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h9"/>
                        </svg>
                        Восстановить доступ
                    </button>
                    {% endif %}

                    <!-- 4. Обновить данные -->
                    <button type="button" 
                            class="btn btn-info"
                            hx-post="{% url 'manual_refresh_access' visit.id %}"
                            hx-trigger="click"
                            hx-swap="none"
                            hx-indicator="#refresh-spinner">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"/>
                            <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>
                        </svg>
                        Обновить
                        <span id="refresh-spinner" class="spinner-border spinner-border-sm ms-2 d-none"></span>
                    </button>
                </div>

                <!-- Опасная зона -->
                {% if perms.visitors.delete_visit or user.is_superuser %}
                <div class="mt-4 p-3 bg-danger-lt rounded">
                    <h4 class="text-danger">⚠️ Опасная зона</h4>
                    <p class="mb-2">Удаление Person из HikCentral необратимо и приведет к удалению:</p>
                    <ul>
                        <li>Фото лица из базы данных HCP</li>
                        <li>Всех прав доступа</li>
                        <li>Истории проходов (может быть)</li>
                    </ul>
                    <button type="button" 
                            class="btn btn-danger" 
                            data-bs-toggle="modal" 
                            data-bs-target="#deletePersonModal">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <line x1="4" y1="7" x2="20" y2="7"/>
                            <line x1="10" y1="11" x2="10" y2="17"/>
                            <line x1="14" y1="11" x2="14" y2="17"/>
                            <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/>
                            <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>
                        </svg>
                        Удалить Person из HikCentral
                    </button>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Модальные окна -->
<!-- 1. Modal: Заблокировать доступ -->
<div class="modal fade" id="revokeAccessModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'manual_revoke_access' visit.id %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title">Заблокировать доступ</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Вы уверены, что хотите заблокировать доступ для гостя <strong>{{ visit.guest.full_name }}</strong>?</p>
                    <div class="mb-3">
                        <label class="form-label">Причина блокировки:</label>
                        <textarea name="reason" class="form-control" rows="3" required></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn" data-bs-dismiss="modal">Отмена</button>
                    <button type="submit" class="btn btn-danger">Заблокировать</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- 2. Modal: Продлить доступ -->
<div class="modal fade" id="extendAccessModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'manual_extend_access' visit.id %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title">Продлить доступ</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Текущий период доступа: до <strong>{{ visit.expected_exit_time|date:"Y-m-d H:i" }}</strong></p>
                    <div class="mb-3">
                        <label class="form-label">Продлить на:</label>
                        <select name="extend_hours" class="form-select" required>
                            <option value="1">1 час</option>
                            <option value="2">2 часа</option>
                            <option value="3">3 часа</option>
                            <option value="6">6 часов</option>
                            <option value="12">12 часов</option>
                            <option value="24">24 часа</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Или укажите новое время выхода:</label>
                        <input type="datetime-local" name="new_exit_time" class="form-control">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn" data-bs-dismiss="modal">Отмена</button>
                    <button type="submit" class="btn btn-warning">Продлить</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- 3. Modal: Восстановить доступ -->
<div class="modal fade" id="restoreAccessModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'manual_restore_access' visit.id %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title">Восстановить доступ</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Восстановить доступ для гостя <strong>{{ visit.guest.full_name }}</strong>?</p>
                    <div class="mb-3">
                        <label class="form-label">Период доступа до:</label>
                        <input type="datetime-local" name="valid_until" class="form-control" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn" data-bs-dismiss="modal">Отмена</button>
                    <button type="submit" class="btn btn-success">Восстановить</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- 4. Modal: Удалить Person -->
<div class="modal fade" id="deletePersonModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'manual_delete_person_hcp' visit.id %}">
                {% csrf_token %}
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title">⚠️ ОПАСНОЕ ДЕЙСТВИЕ</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p class="text-danger"><strong>ВНИМАНИЕ!</strong> Это действие необратимо!</p>
                    <p>Будет удалено из HikCentral:</p>
                    <ul>
                        <li>Person ID: <code>{{ visit.hikcentral_person_id }}</code></li>
                        <li>Фото лица</li>
                        <li>Все права доступа</li>
                    </ul>
                    <div class="mb-3">
                        <label class="form-label">Для подтверждения введите: <code>DELETE</code></label>
                        <input type="text" name="confirm" class="form-control" pattern="DELETE" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn" data-bs-dismiss="modal">Отмена</button>
                    <button type="submit" class="btn btn-danger">Удалить навсегда</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endif %}
```

---

### Шаг 2: Backend Views (visitors/views.py)

**Добавить в конец файла:**

```python
# ============================================================================
# Manual Access Control Views
# ============================================================================

from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@login_required
@require_POST
def manual_revoke_access(request, visit_id):
    """Ручная блокировка доступа в HikCentral.
    
    Вызывается кнопкой "Заблокировать доступ" на visit_detail.
    """
    visit = get_object_or_404(Visit, pk=visit_id)
    
    # Проверка прав (только staff или security group)
    if not (request.user.is_staff or 
            request.user.groups.filter(name__in=['Security', 'Reception']).exists()):
        messages.error(request, "У вас нет прав для блокировки доступа")
        return redirect('visit_detail', visit_id=visit_id)
    
    # Проверка статуса
    if not visit.access_granted or visit.access_revoked:
        messages.warning(request, "Доступ уже отозван или не был выдан")
        return redirect('visit_detail', visit_id=visit_id)
    
    # Получение причины из формы
    reason = request.POST.get('reason', 'Manual revoke via UI')
    
    try:
        # Запускаем Celery task для отзыва доступа
        from hikvision_integration.tasks import revoke_access_level_task
        
        result = revoke_access_level_task.apply_async(
            args=[visit.id],
            kwargs={'manual_reason': reason, 'actor_username': request.user.username},
            countdown=2
        )
        
        # Обновляем локальный статус сразу (оптимистично)
        visit.access_revoked = True
        visit.save(update_fields=['access_revoked'])
        
        # Audit log
        AuditLog.objects.create(
            action='MANUAL_REVOKE',
            model='Visit',
            object_id=str(visit.pk),
            actor=request.user,
            changes={'reason': reason, 'celery_task_id': str(result.id)},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(
            request,
            f"✅ Доступ для {visit.guest.full_name} заблокирован. "
            f"Task ID: {result.id}"
        )
        logger.info(
            f"Manual revoke access: visit_id={visit_id}, user={request.user.username}, "
            f"task_id={result.id}, reason={reason}"
        )
        
    except Exception as e:
        logger.exception(f"Failed to revoke access manually: {e}")
        messages.error(request, f"❌ Ошибка блокировки доступа: {e}")
    
    return redirect('visit_detail', visit_id=visit_id)


@login_required
@require_POST
def manual_extend_access(request, visit_id):
    """Ручное продление периода доступа.
    
    Два режима:
    1. Продлить на X часов (extend_hours)
    2. Установить новое время (new_exit_time)
    """
    visit = get_object_or_404(Visit, pk=visit_id)
    
    # Проверка прав
    if not (request.user.is_staff or 
            request.user.groups.filter(name__in=['Security', 'Reception']).exists()):
        messages.error(request, "У вас нет прав для продления доступа")
        return redirect('visit_detail', visit_id=visit_id)
    
    try:
        # Режим 1: Продлить на X часов
        if request.POST.get('extend_hours'):
            hours = int(request.POST['extend_hours'])
            current_exit = visit.expected_exit_time or timezone.now()
            new_exit_time = current_exit + timedelta(hours=hours)
            mode = f"Extended by {hours}h"
        
        # Режим 2: Новое время
        elif request.POST.get('new_exit_time'):
            new_exit_str = request.POST['new_exit_time']
            # Конвертируем из HTML datetime-local в aware datetime
            from django.utils.dateparse import parse_datetime
            new_exit_time = parse_datetime(new_exit_str)
            if new_exit_time and timezone.is_naive(new_exit_time):
                new_exit_time = timezone.make_aware(new_exit_time)
            mode = "Set new time"
        else:
            messages.error(request, "Не указан новый период доступа")
            return redirect('visit_detail', visit_id=visit_id)
        
        # Валидация: не в прошлом
        if new_exit_time < timezone.now():
            messages.error(request, "Нельзя установить время в прошлом")
            return redirect('visit_detail', visit_id=visit_id)
        
        # Запуск Celery task
        from hikvision_integration.tasks import update_person_validity_task
        
        result = update_person_validity_task.apply_async(
            args=[visit.id],
            kwargs={
                'new_exit_time': new_exit_time.isoformat(),
                'actor_username': request.user.username
            },
            countdown=2
        )
        
        # Обновляем локально
        old_exit = visit.expected_exit_time
        visit.expected_exit_time = new_exit_time
        visit.save(update_fields=['expected_exit_time'])
        
        # Audit
        AuditLog.objects.create(
            action='MANUAL_EXTEND',
            model='Visit',
            object_id=str(visit.pk),
            actor=request.user,
            changes={
                'old_exit': old_exit.isoformat() if old_exit else None,
                'new_exit': new_exit_time.isoformat(),
                'mode': mode,
                'celery_task_id': str(result.id)
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(
            request,
            f"✅ Доступ продлён до {new_exit_time.strftime('%Y-%m-%d %H:%M')}. "
            f"Task ID: {result.id}"
        )
        
    except Exception as e:
        logger.exception(f"Failed to extend access: {e}")
        messages.error(request, f"❌ Ошибка продления доступа: {e}")
    
    return redirect('visit_detail', visit_id=visit_id)


@login_required
@require_POST
def manual_restore_access(request, visit_id):
    """Восстановление доступа (после блокировки)."""
    visit = get_object_or_404(Visit, pk=visit_id)
    
    # Проверка прав
    if not request.user.is_staff:
        messages.error(request, "Только администраторы могут восстанавливать доступ")
        return redirect('visit_detail', visit_id=visit_id)
    
    if not visit.access_revoked:
        messages.warning(request, "Доступ не был отозван")
        return redirect('visit_detail', visit_id=visit_id)
    
    try:
        # Получаем новый период
        valid_until_str = request.POST.get('valid_until')
        from django.utils.dateparse import parse_datetime
        valid_until = parse_datetime(valid_until_str)
        if valid_until and timezone.is_naive(valid_until):
            valid_until = timezone.make_aware(valid_until)
        
        # Запускаем повторную выдачу доступа
        from hikvision_integration.tasks import assign_access_level_task
        
        # Обновляем expected_exit_time
        visit.expected_exit_time = valid_until
        visit.access_revoked = False
        visit.save(update_fields=['expected_exit_time', 'access_revoked'])
        
        result = assign_access_level_task.apply_async(
            args=[visit.id],
            countdown=2
        )
        
        # Audit
        AuditLog.objects.create(
            action='MANUAL_RESTORE',
            model='Visit',
            object_id=str(visit.pk),
            actor=request.user,
            changes={
                'valid_until': valid_until.isoformat(),
                'celery_task_id': str(result.id)
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(request, f"✅ Доступ восстановлен до {valid_until.strftime('%Y-%m-%d %H:%M')}")
        
    except Exception as e:
        logger.exception(f"Failed to restore access: {e}")
        messages.error(request, f"❌ Ошибка восстановления: {e}")
    
    return redirect('visit_detail', visit_id=visit_id)


@login_required
@require_POST
def manual_refresh_access(request, visit_id):
    """Синхронизация данных с HikCentral (AJAX/htmx endpoint).
    
    Получает актуальные данные Person из HCP и обновляет Visit.
    """
    visit = get_object_or_404(Visit, pk=visit_id)
    
    if not visit.hikcentral_person_id:
        return JsonResponse({'error': 'No HikCentral Person ID'}, status=400)
    
    try:
        from hikvision_integration.models import HikCentralServer
        from hikvision_integration.services import (
            HikCentralSession, 
            get_person_hikcentral
        )
        
        # Получаем сервер
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            return JsonResponse({'error': 'No HCP server configured'}, status=500)
        
        # Создаём сессию
        session = HikCentralSession(server)
        
        # Получаем данные Person
        person_data = get_person_hikcentral(session, visit.hikcentral_person_id)
        
        if not person_data:
            return JsonResponse({'error': 'Person not found in HCP'}, status=404)
        
        # Обновляем Visit
        # person_data: {'personId': '...', 'personCode': '...', 'validTo': '...', ...}
        if 'validTo' in person_data:
            from django.utils.dateparse import parse_datetime
            valid_to = parse_datetime(person_data['validTo'])
            if valid_to and timezone.is_naive(valid_to):
                valid_to = timezone.make_aware(valid_to)
            visit.expected_exit_time = valid_to
        
        visit.save()
        
        messages.success(request, "✅ Данные обновлены из HikCentral")
        logger.info(f"Manual refresh: visit_id={visit_id}, user={request.user.username}")
        
        return JsonResponse({'success': True, 'person_data': person_data})
        
    except Exception as e:
        logger.exception(f"Failed to refresh from HCP: {e}")
        messages.error(request, f"❌ Ошибка синхронизации: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@permission_required('visitors.delete_visit', raise_exception=True)
def manual_delete_person_hcp(request, visit_id):
    """ОПАСНО: Удаление Person из HikCentral.
    
    Требует подтверждения и права delete_visit.
    """
    visit = get_object_or_404(Visit, pk=visit_id)
    
    # Проверка подтверждения
    if request.POST.get('confirm') != 'DELETE':
        messages.error(request, "Неверное подтверждение. Введите DELETE")
        return redirect('visit_detail', visit_id=visit_id)
    
    if not visit.hikcentral_person_id:
        messages.warning(request, "Нет Person ID в HikCentral")
        return redirect('visit_detail', visit_id=visit_id)
    
    try:
        from hikvision_integration.models import HikCentralServer
        from hikvision_integration.services import (
            HikCentralSession,
            delete_person_hikcentral  # Нужно добавить эту функцию в services.py!
        )
        
        server = HikCentralServer.objects.filter(enabled=True).first()
        if not server:
            messages.error(request, "HCP server not configured")
            return redirect('visit_detail', visit_id=visit_id)
        
        session = HikCentralSession(server)
        person_id = visit.hikcentral_person_id
        
        # Удаляем Person из HCP
        delete_person_hikcentral(session, person_id)
        
        # Обнуляем данные в Visit
        visit.hikcentral_person_id = None
        visit.access_granted = False
        visit.access_revoked = True
        visit.save()
        
        # Audit
        AuditLog.objects.create(
            action='MANUAL_DELETE_PERSON',
            model='Visit',
            object_id=str(visit.pk),
            actor=request.user,
            changes={'deleted_person_id': person_id},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.warning(
            request,
            f"⚠️ Person ID {person_id} удалён из HikCentral. "
            f"Это действие необратимо!"
        )
        logger.warning(
            f"Manual DELETE person: visit_id={visit_id}, person_id={person_id}, "
            f"user={request.user.username}"
        )
        
    except Exception as e:
        logger.exception(f"Failed to delete person from HCP: {e}")
        messages.error(request, f"❌ Ошибка удаления: {e}")
    
    return redirect('visit_detail', visit_id=visit_id)
```

---

### Шаг 3: URL Routes (visitors/urls.py)

**Добавить:**

```python
# В конец urlpatterns добавить:
urlpatterns = [
    # ... existing URLs ...
    
    # Manual Access Control
    path('visit/<int:visit_id>/manual/revoke/', 
         views.manual_revoke_access, 
         name='manual_revoke_access'),
    
    path('visit/<int:visit_id>/manual/extend/', 
         views.manual_extend_access, 
         name='manual_extend_access'),
    
    path('visit/<int:visit_id>/manual/restore/', 
         views.manual_restore_access, 
         name='manual_restore_access'),
    
    path('visit/<int:visit_id>/manual/refresh/', 
         views.manual_refresh_access, 
         name='manual_refresh_access'),
    
    path('visit/<int:visit_id>/manual/delete-person/', 
         views.manual_delete_person_hcp, 
         name='manual_delete_person_hcp'),
]
```

---

### Шаг 4: Добавить недостающие функции в services.py

**В `hikvision_integration/services.py` добавить:**

```python
def delete_person_hikcentral(session: HikCentralSession, person_id: str) -> bool:
    """Удаляет Person из HikCentral Professional.
    
    Args:
        session: HikCentral session
        person_id: ID Person в HCP
        
    Returns:
        True если успешно, False если ошибка
        
    Warning:
        Это действие необратимо! Удаляется:
        - Person record
        - Face data (фото)
        - Access rights
        - История может быть потеряна (зависит от HCP версии)
    """
    logger.warning(
        f"HikCentral: DELETING Person {person_id} - THIS IS IRREVERSIBLE!"
    )
    
    try:
        # Endpoint: DELETE /artemis/api/resource/v1/person/single/delete
        # Или: POST /artemis/api/resource/v1/person/single/delete с personIds
        
        payload = {
            'personIds': str(person_id)
        }
        
        resp = session._make_request(
            'POST',
            '/artemis/api/resource/v1/person/single/delete',
            data=payload
        )
        
        result = resp.json()
        
        if result.get('code') != '0':
            logger.error(
                f"HikCentral: Failed to delete person {person_id}: {result.get('msg')}"
            )
            return False
        
        logger.info(
            f"HikCentral: Successfully deleted person {person_id}"
        )
        return True
        
    except Exception as e:
        logger.exception(f"HikCentral: Failed to delete person {person_id}: {e}")
        return False


def get_person_hikcentral(session: HikCentralSession, person_id: str) -> dict:
    """Получает информацию о Person из HikCentral.
    
    Args:
        session: HikCentral session
        person_id: ID Person в HCP
        
    Returns:
        Dict с данными Person или пустой dict при ошибке
        
    Example response:
        {
            'personId': '12345678',
            'personCode': 'guest_123',
            'personName': 'Иван Иванов',
            'validFrom': '2025-10-06T10:00:00+08:00',
            'validTo': '2025-10-06T18:00:00+08:00',
            'orgIndexCode': '1',
            'status': 1  # 1=active, 0=inactive
        }
    """
    logger.info(f"HikCentral: Getting person info for {person_id}")
    
    try:
        resp = session._make_request(
            'POST',
            '/artemis/api/resource/v1/person/personId/personInfo',
            data={'personId': str(person_id)}
        )
        
        result = resp.json()
        
        if result.get('code') != '0' or not result.get('data'):
            logger.warning(
                f"HikCentral: Person {person_id} not found or error: {result.get('msg')}"
            )
            return {}
        
        person_data = result['data']
        logger.info(
            f"HikCentral: Got person {person_id}: {person_data.get('personName')}"
        )
        
        return person_data
        
    except Exception as e:
        logger.exception(f"HikCentral: Failed to get person {person_id}: {e}")
        return {}
```

---

## ✅ Итоговая проверка

### 1. Файлы для изменения:

```
✅ templates/visitors/visit_detail.html  - Добавить UI панель
✅ visitors/views.py                     - 5 новых views
✅ visitors/urls.py                      - 5 новых URL patterns
✅ hikvision_integration/services.py    - 2 новые функции
```

### 2. Зависимости (уже есть):

```python
✅ HikCentralSession          - services.py (есть)
✅ assign_access_level_task   - tasks.py (есть)
✅ revoke_access_level_task   - tasks.py (есть)
✅ update_person_validity_task - tasks.py (есть)
✅ AuditLog                    - models.py (есть)
✅ Bootstrap 5 modals          - base.html (есть)
✅ htmx                        - base.html (есть)
```

### 3. Права доступа:

```python
# Кто может управлять?
- Заблокировать/Продлить: staff OR (Security/Reception groups)
- Восстановить: только staff
- Удалить Person: требуется permission 'visitors.delete_visit'
```

---

## 🎨 Как это будет выглядеть?

```
╔═══════════════════════════════════════════════════════════╗
║  Детали визита №123                                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  [Информация о госте]  |  [Информация о визите]          ║
║                                                           ║
║  ┌────────────────────────────────────────────────────┐  ║
║  │  🔒 Ручное управление доступом HikCentral          │  ║
║  ├────────────────────────────────────────────────────┤  ║
║  │                                                      │  ║
║  │  HikCentral Person ID: 12345678                     │  ║
║  │  Статус доступа: ✅ АКТИВЕН                         │  ║
║  │  Период доступа: 2025-10-06 10:00 → 18:00          │  ║
║  │  Первый проход: 2025-10-06 10:15:32                │  ║
║  │                                                      │  ║
║  │  Действия:                                          │  ║
║  │  [🚫 Заблокировать] [⏱️ Продлить] [🔄 Обновить]   │  ║
║  │                                                      │  ║
║  │  ⚠️ Опасная зона:                                   │  ║
║  │  [🗑️ Удалить Person из HikCentral]                 │  ║
║  └────────────────────────────────────────────────────┘  ║
║                                                           ║
║  [← Назад к истории визитов]                             ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🚀 Тестирование

### Сценарий 1: Продление доступа

```
1. Открыть visit_detail для гостя с access_granted=True
2. Нажать [⏱️ Продлить доступ]
3. Выбрать "Продлить на 2 часа"
4. Нажать [Продлить]
5. Проверить: Visit.expected_exit_time увеличилось на 2 часа
6. Проверить: В HCP validity period обновился
7. Проверить: В AuditLog появилась запись MANUAL_EXTEND
```

### Сценарий 2: Блокировка доступа

```
1. Открыть visit_detail для активного гостя
2. Нажать [🚫 Заблокировать доступ]
3. Ввести причину: "Нарушение правил"
4. Нажать [Заблокировать]
5. Проверить: Visit.access_revoked = True
6. Проверить: В HCP access level отозван
7. Попробовать пройти турникет → доступ запрещён
```

### Сценарий 3: Обновление данных

```
1. Вручную изменить validity в HCP UI
2. В Django UI нажать [🔄 Обновить]
3. Проверить: Visit.expected_exit_time синхронизировалось с HCP
```

---

## 📊 Статистика использования

После реализации можно отслеживать:

```sql
-- Сколько раз использовали Manual UI
SELECT 
    action, 
    COUNT(*) as count,
    actor__username
FROM visitors_auditlog
WHERE action IN ('MANUAL_REVOKE', 'MANUAL_EXTEND', 'MANUAL_RESTORE', 'MANUAL_DELETE_PERSON')
GROUP BY action, actor__username
ORDER BY count DESC;
```

---

## 💡 Дополнительные фичи (опционально)

### 1. История изменений на странице

```django-html
<div class="card mt-3">
    <div class="card-header">История ручных действий</div>
    <div class="card-body">
        <ul class="list-unstyled">
            {% for log in audit_logs %}
            <li>
                <strong>{{ log.created_at|date:"Y-m-d H:i" }}</strong> - 
                {{ log.get_action_display }} 
                by <em>{{ log.actor.username }}</em>
                {% if log.changes %}
                <details class="mt-1">
                    <summary>Детали</summary>
                    <pre>{{ log.changes|pprint }}</pre>
                </details>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </div>
</div>
```

### 2. Bulk операции (для Reception)

```django-html
<!-- На странице current_guests.html -->
<form method="post" action="{% url 'bulk_extend_access' %}">
    {% csrf_token %}
    <table>
        <tr>
            <td><input type="checkbox" name="visit_ids" value="1"></td>
            <td>Иван Иванов</td>
            <td>До 18:00</td>
        </tr>
        <tr>
            <td><input type="checkbox" name="visit_ids" value="2"></td>
            <td>Петр Петров</td>
            <td>До 18:00</td>
        </tr>
    </table>
    <button type="submit">Продлить выбранных на 2 часа</button>
</form>
```

---

## 📝 Резюме

**Manual UI = 4 основные кнопки:**

1. 🚫 **Заблокировать** - revoke access в HCP
2. ⏱️ **Продлить** - update validity period
3. 🔄 **Обновить** - sync с HCP
4. 🗑️ **Удалить** - delete person (опасно!)

**Технический стек:**

- Frontend: Bootstrap 5 modals + htmx
- Backend: Django views + Celery tasks
- API: HikCentral OpenAPI (services.py)
- Audit: AuditLog для каждого действия

**Время реализации:** ~3-4 часа

**Что получите:**

- ✅ Гибкое управление доступом без консоли HCP
- ✅ Полный audit trail всех действий
- ✅ Удобный UI для reception/security
- ✅ Права доступа по группам

Готов начать реализацию? 🚀
