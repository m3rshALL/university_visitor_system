"""
Оптимизация и кэширование для системы посетителей университета

Этот файл содержит рекомендации и готовый код для оптимизации приложения.
Эти изменения помогут уменьшить нагрузку на сервер и ускорить работу системы.
"""

"""
1. Добавление кэширования для представлений

Добавьте следующие декораторы для key views:

@cache_page(60 * 5)  # Кэширование на 5 минут
@vary_on_cookie     # Разные кэши для разных пользователей

Например:
@login_required
@cache_page(60 * 5)  
@vary_on_cookie
def current_guests_view(request):
    ...

@login_required
@cache_control(private=True)  # Приватное кэширование
def visit_history_view(request):
    # Создаем ключ кэша на основе GET-параметров и пользователя
    cache_key = f"visit_history_{request.user.id}_{hash(frozenset(request.GET.items()))}"
    
    # Пытаемся получить данные из кэша
    cached_data = cache.get(cache_key)
    if cached_data and not request.GET.get('nocache'):  # Добавляем возможность обойти кэш
        return render(request, 'visitors/visit_history.html', cached_data)
    
    # ... остальной код view ...
    
    # Сохраняем результат в кэше на 3 минуты
    cache.set(cache_key, context, 60 * 3)
    
    return render(request, 'visitors/visit_history.html', context)
"""

"""
2. Кэширование запросов к базе данных

Используйте встроенное кэширование запросов:

from django.core.cache import cache

# Для часто повторяющихся запросов:
def get_some_data():
    cache_key = "some_data_key"
    result = cache.get(cache_key)
    if result is None:
        # Запрос к БД только если нет в кэше
        result = SomeModel.objects.filter(...).all()
        cache.set(cache_key, result, 60 * 30)  # кэш на 30 минут
    return result
"""

"""
3. Кэширование на уровне шаблонов

В шаблонах используйте:

{% load cache %}
{% cache 300 "sidebar" %}
    ... сложный блок, который требует много вычислений ...
{% endcache %}

Это позволит кэшировать тяжелые части шаблонов.
"""

"""
4. Оптимизация запросов к БД

- Используйте select_related() и prefetch_related() для оптимизации запросов (уже сделано)
- Избегайте повторных запросов к одним и тем же данным
- Используйте обработку в базе данных вместо Python (annotate, aggregate)
- Используйте метод only() для выборки только нужных полей
- Используйте метод values() или values_list() для чтения только нужных полей
"""

"""
5. Настройка Redis как кэша Django

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "TIMEOUT": 300, # 5 минут по умолчанию
    }
}

# Хранение сессий в Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
"""

"""
6. Настройка кэширования статических файлов

В middleware добавьте:
'django.middleware.cache.UpdateCacheMiddleware',
'django.middleware.common.CommonMiddleware',
'django.middleware.cache.FetchFromCacheMiddleware',

В settings.py:
# Настройки для Nginx/Apache
STATIC_ROOT = '/path/to/static/files'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Cache settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10 минут
CACHE_MIDDLEWARE_KEY_PREFIX = 'visitor_system'
"""

"""
7. Оптимизация Nginx/Apache для статических файлов

server {
    listen 80;
    server_name example.com;

    location /static/ {
        alias /path/to/static/;
        expires 30d;  # Кэширование в браузере на 30 дней
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        alias /path/to/media/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        # ...
    }
}
"""

"""
8. Мониторинг и профилирование

Используйте Django Debug Toolbar или django-silk для мониторинга производительности:

pip install django-debug-toolbar

В settings.py:
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
"""

"""
9. Асинхронная обработка тяжелых задач

Для тяжелых операций (например, создание Excel-отчетов, отправка email)
используйте Celery:

@app.task
def generate_excel_report(filters):
    # Долгое создание отчета
    pass

# В представлении:
def generate_report_view(request):
    task = generate_excel_report.delay(request.GET)
    return redirect('report_status', task_id=task.id)
"""

"""
10. Использование кэширования в моделях

class SomeModel(models.Model):
    # ... поля модели ...
    
    @cached_property
    def complex_calculation(self):
        # Тяжелый расчет, который будет кэшироваться на время жизни объекта
        result = # ... сложные вычисления ...
        return result
"""

"""
11. Пагинация и ленивая загрузка

Всегда используйте пагинацию для больших наборов данных:

objects = MyModel.objects.all()
paginator = Paginator(objects, 20)  # 20 объектов на страницу
page = request.GET.get('page')
page_obj = paginator.get_page(page)
"""

"""
12. Использование индексов в базе данных

Для часто запрашиваемых полей добавьте индексы:

class Visit(models.Model):
    entry_time = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
"""

"""
13. Сжатие данных

Включите сжатие gzip для HTTP-ответов, добавив в middleware:

'django.middleware.gzip.GZipMiddleware',
"""

"""
14. Использование Content Delivery Network (CDN)

Для общедоступных статических файлов (JS, CSS) используйте CDN:

# В шаблонах:
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
"""

"""
15. Оптимизация шаблонов Django

- Избегайте сложных вычислений в шаблонах
- Используйте template tags для повторяющихся блоков
- Разделяйте большие шаблоны на частичные с include
"""
