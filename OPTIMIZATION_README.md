# Оптимизация и кэширование для системы посетителей университета

В этом документе описаны шаги и рекомендации по оптимизации производительности системы учета посетителей.

## Содержание

1. [Настройка кэширования](#настройка-кэширования)
2. [Оптимизация представлений](#оптимизация-представлений)
3. [Оптимизация запросов к базе данных](#оптимизация-запросов-к-базе-данных)
4. [Кэширование шаблонов](#кэширование-шаблонов)
5. [Оптимизация статических файлов](#оптимизация-статических-файлов)
6. [Мониторинг и профилирование](#мониторинг-и-профилирование)

## Настройка кэширования

### 1. Установка Redis

Redis используется как быстрое хранилище для кэша Django.

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# Windows
# Скачайте Redis с https://github.com/microsoftarchive/redis/releases
```

### 2. Настройка Django для работы с Redis

Установите необходимые пакеты:

```bash
pip install django-redis
```

Добавьте в `settings.py`:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "TIMEOUT": 300,  # 5 минут
    }
}

# Хранение сессий в Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

## Оптимизация представлений

### 1. Кэширование представлений

Используйте декораторы для кэширования представлений:

```python
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_cookie

@cache_page(60 * 5)  # Кэш на 5 минут
@vary_on_cookie     # Разные кэши для разных пользователей
def my_view(request):
    # ...
```

### 2. Использование кэша для часто запрашиваемых данных

```python
from django.core.cache import cache

def get_department_employees(department_id):
    cache_key = f"dept_employees_{department_id}"
    employees = cache.get(cache_key)
    
    if employees is None:
        employees = Employee.objects.filter(department_id=department_id)
        cache.set(cache_key, employees, 60 * 30)  # Кэш на 30 минут
    
    return employees
```

### 3. Добавьте middleware для кэширования и сжатия

В `settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # Должен быть первым
    'django.middleware.gzip.GZipMiddleware',
    # ... другие middleware ...
    'django.middleware.cache.FetchFromCacheMiddleware',  # Должен быть последним
]
```

## Оптимизация запросов к базе данных

### 1. Используйте `select_related` и `prefetch_related`

```python
# Вместо этого:
visits = Visit.objects.all()
for v in visits:
    print(v.guest.name, v.department.name)  # Много запросов к БД

# Используйте это:
visits = Visit.objects.select_related('guest', 'department').all()
for v in visits:
    print(v.guest.name, v.department.name)  # Всего 1 запрос к БД
```

### 2. Используйте индексы для часто запрашиваемых полей

В моделях:

```python
class Visit(models.Model):
    entry_time = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
```

### 3. Избегайте повторных запросов

Используйте `cached_property` для методов моделей, требующих запросов к БД:

```python
from django.utils.functional import cached_property

class Department(models.Model):
    name = models.CharField(max_length=100)
    
    @cached_property
    def employee_count(self):
        return self.employees.count()
```

## Кэширование шаблонов

### 1. Кэширование фрагментов шаблона

В шаблонах Django:

```django
{% load cache %}

{% cache 300 "sidebar" %}
    {# Сложный фрагмент шаблона, который медленно рендерится #}
{% endcache %}
```

### 2. Используйте custom template tags для более гибкого кэширования

См. файл `cache_tags.py` в проекте для примеров пользовательских тегов.

## Оптимизация статических файлов

### 1. Настройка статических файлов для production

В `settings.py`:

```python
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
```

### 2. Настройка Nginx для кэширования статики

```nginx
server {
    # ...
    location /static/ {
        alias /path/to/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }
    # ...
}
```

## Мониторинг и профилирование

### 1. Установка Django Debug Toolbar

```bash
pip install django-debug-toolbar
```

В `settings.py`:

```python
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

### 2. Использование custom middleware для мониторинга

См. файл `performance_middleware.py` для примеров middleware для отслеживания SQL запросов и потребления ресурсов.

## Дополнительные рекомендации

1. **Асинхронность**: Используйте Celery для тяжелых задач (генерация отчетов, отправка email).
2. **Пагинация**: Всегда используйте пагинацию для больших наборов данных.
3. **Ленивая загрузка**: Используйте AJAX для ленивой загрузки контента.
4. **CDN**: Используйте CDN для статических файлов в production.

## Инструкции по применению

1. Скопируйте настройки из `settings_optimization.py` в ваш основной `settings.py`
2. Добавьте middleware из `performance_middleware.py` в `MIDDLEWARE`
3. Используйте утилиты из `cache_utils.py` для декорирования функций
4. Используйте template tags из `cache_tags.py` в шаблонах

## Мониторинг эффективности

После внедрения оптимизаций, мониторьте:

1. Время ответа сервера
2. Количество запросов к БД
3. Использование памяти и CPU
4. Hit/Miss соотношение для кэша

Дополнительные инструменты: New Relic, Datadog, Django Silk.
