# WebPush Уведомления

Реализация push-уведомлений для браузера в системе пропусков AITU.

## Установка и настройка

### 1. Установка библиотеки

```bash
pip install django-webpush
```

### 2. Генерация VAPID ключей

Запустите скрипт для генерации ключей:

```bash
python generate_vapid_keys.py
```

Добавьте полученные ключи в `.env` файл:

```env
VAPID_PRIVATE_KEY=your-private-key
VAPID_PUBLIC_KEY=your-public-key
VAPID_ADMIN_EMAIL=your-email@example.com
```

### 3. Применение миграций

```bash
python manage.py migrate notifications
```

### 4. Настройка settings.py

Библиотека `webpush` уже добавлена в `INSTALLED_APPS` и настроены `WEBPUSH_SETTINGS`.

## Использование

### Отправка уведомлений в коде

#### Простая отправка

```python
from notifications.utils import send_webpush_notification

# Отправка уведомления пользователю
result = send_webpush_notification(
    user=user,
    title="Гость прибыл",
    body="К вам прибыл гость Иван Иванов"
)

if result['success']:
    print(f"Уведомление отправлено {result['sent_count']} подписчикам")
else:
    print(f"Ошибки: {result['errors']}")
```

#### Создание уведомления с автоматической отправкой

```python
from notifications.utils import create_notification_with_webpush

notification, webpush_result = create_notification_with_webpush(
    recipient=user,
    title="Визит одобрен",
    message="Ваш визит был одобрен администратором",
    notification_type="visit_approved",
    action_url="/visits/123/",
    send_push=True
)
```

#### Отправка нескольким пользователям

```python
from notifications.utils import send_webpush_to_multiple_users
from django.contrib.auth.models import User

# Отправка всем сотрудникам
users = User.objects.filter(is_staff=True)
result = send_webpush_to_multiple_users(
    users=users,
    title="Системное уведомление",
    body="Плановое обслуживание системы в 18:00"
)
```

### Интеграция с существующими уведомлениями

Пример интеграции в существующую функцию уведомлений о прибытии гостя:

```python
# В visitors/signals.py или views.py
from notifications.utils import create_notification_with_webpush

def notify_employee_guest_arrival(visit):
    """Уведомляет сотрудника о прибытии гостя"""
    
    # Создаем уведомление в БД и отправляем WebPush
    notification, webpush_result = create_notification_with_webpush(
        recipient=visit.employee,
        title=f"К Вам прибыл гость: {visit.guest.full_name}",
        message=f"Цель визита: {visit.purpose}",
        notification_type="guest_arrived",
        action_url=f"/visits/{visit.id}/",
        related_object_id=visit.id,
        related_object_type="visit"
    )
    
    # Дополнительно отправляем email (как было раньше)
    send_guest_arrival_email(visit)
```

### Типы уведомлений

Поддерживаемые типы уведомлений:

- `visit_approved` - Визит одобрен
- `visit_denied` - Визит отклонен  
- `visit_reminder` - Напоминание о визите
- `guest_arrived` - Гость прибыл
- `booking_confirmed` - Бронирование подтверждено
- `booking_cancelled` - Бронирование отменено
- `system` - Системное уведомление

## Фронтенд

### Компонент настроек

Используйте готовый компонент для настройки уведомлений:

```django
<!-- В любом шаблоне -->
{% include 'notifications/webpush_settings.html' %}
```

### Программное управление

JavaScript API для управления подписками:

```javascript
// Подписаться на уведомления
webPushManager.subscribe().then(success => {
    if (success) {
        console.log('Подписка оформлена');
    }
});

// Отписаться от уведомлений
webPushManager.unsubscribe().then(success => {
    if (success) {
        console.log('Подписка отменена');
    }
});

// Проверить статус поддержки
if (webPushManager.isSupported) {
    console.log('WebPush поддерживается');
}
```

## Модели

### WebPushSubscription

Хранит информацию о подписках пользователей:

- `user` - Пользователь
- `endpoint` - Endpoint для отправки
- `p256dh_key` - Ключ шифрования
- `auth_key` - Ключ аутентификации
- `device_name` - Название устройства
- `is_active` - Активна ли подписка

### WebPushMessage

Лог отправленных сообщений:

- `subscription` - Подписка
- `notification` - Связанное уведомление
- `title` - Заголовок
- `body` - Текст
- `success` - Успешность отправки
- `error_message` - Сообщение об ошибке

## Администрирование

### Django Admin

Все модели доступны в админ панели:

- Просмотр и управление уведомлениями
- Управление подписками (активация/деактивация)
- Просмотр логов отправки

### Тестирование

Для тестирования WebPush доступны кнопки для администраторов в компоненте настроек.

### API для тестирования

```bash
# Отправка тестового уведомления (только для staff)
curl -X POST /notifications/send-notification/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "title": "Тест",
    "body": "Тестовое уведомление",
    "user_id": 1
  }'
```

## Безопасность

- VAPID ключи обеспечивают аутентификацию сервера
- Подписки привязаны к пользователям
- Автоматическая деактивация недействительных подписок
- Все запросы защищены CSRF токенами

## Поддержка браузеров

WebPush поддерживается в:
- Chrome/Chromium 50+
- Firefox 44+
- Safari 16+
- Edge 79+

Автоматическая проверка поддержки на клиенте.

## Мониторинг

Если настроен Prometheus, доступны метрики:
- `webpush_send_total` - Общее количество отправок
- `webpush_send_failures_total` - Количество ошибок

## Устранение проблем

### Пользователь не получает уведомления

1. Проверьте, что браузер поддерживает WebPush
2. Убедитесь, что пользователь дал разрешение на уведомления
3. Проверьте активность подписки в админке
4. Проверьте логи в модели WebPushMessage

### Ошибки VAPID

Убедитесь, что:
- VAPID ключи правильно сгенерированы
- Ключи добавлены в переменные окружения
- Сервер перезапущен после добавления ключей

### Service Worker не регистрируется

- Проверьте, что файл serviceworker.js доступен
- Убедитесь, что сайт работает по HTTPS (требование для production)
- Проверьте консоль браузера на ошибки
