"""
Настройки для оптимизации Django-приложения.
Включите эти настройки в ваш основной settings.py.
"""

# --- Кэширование Django ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50, "socket_connect_timeout": 5},
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,  # Не падать, если Redis недоступен
        },
        "TIMEOUT": 300,  # 5 минут по умолчанию
        "KEY_PREFIX": "visitor_system",  # Префикс для ключей кэша
    }
}

# --- Настройки для сессий ---
# Хранение сессий в Redis для лучшей производительности
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
# Настройки кук сессий
SESSION_COOKIE_AGE = 86400 * 14  # 14 дней
SESSION_COOKIE_SECURE = True  # Только по HTTPS

# --- Настройки для кэширования представлений ---
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600  # Время кэширования для view cache middleware
CACHE_MIDDLEWARE_KEY_PREFIX = "visitor_system"

# --- Настройки статических файлов ---
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
# Добавляем compressor для JS и CSS
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True
COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.CSSMinFilter",
]
COMPRESS_JS_FILTERS = ["compressor.filters.jsmin.JSMinFilter"]

# --- Дополнительные middleware для оптимизации ---
EXTRA_MIDDLEWARE = [
    # Кэширование представлений - добавьте в начало MIDDLEWARE
    "django.middleware.cache.UpdateCacheMiddleware",
    # Сжатие ответов gzip - добавьте перед CommonMiddleware
    "django.middleware.gzip.GZipMiddleware",
    # Кэширование после обработки представления - добавьте в конец MIDDLEWARE
    "django.middleware.cache.FetchFromCacheMiddleware",
    # Custom middleware для отладки и оптимизации (только в DEBUG)
    "visitors.performance_middleware.QueryCountDebugMiddleware",
    "visitors.performance_middleware.ConditionalCacheMiddleware",
]

# --- Оптимизация настроек ORM ---
# Размер кэша словарей для SQL запросов
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # Максимальное количество полей в форме

# --- Настройки для memcached ---
"""
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300,
        'OPTIONS': {
            'server_max_value_length': 1024 * 1024 * 1024,  # 1GB
        }
    }
}
"""

# --- Дополнительные оптимизации для безопасности ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"  # Запретить отображение в <iframe>

# --- Оптимизация загрузки медиа-файлов ---
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB - максимальный размер файла в памяти
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
FILE_UPLOAD_PERMISSIONS = 0o644

# --- Настройки для использования CDN (если нужно) ---
"""
# Пример для Amazon S3 с django-storages
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_CUSTOM_DOMAIN = 'cdn.yourdomain.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
"""

# --- Настройки для django-debug-toolbar (только для разработки) ---
if DEBUG:
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.history.HistoryPanel",
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ]
    
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }
