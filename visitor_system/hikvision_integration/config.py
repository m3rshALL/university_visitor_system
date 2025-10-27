# HikCentral API Optimization Settings
# Добавьте эти настройки в ваш Django settings.py

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

# Максимальное количество API вызовов в окне времени
HIKCENTRAL_RATE_LIMIT_CALLS = 10

# Окно времени для rate limiting в секундах
HIKCENTRAL_RATE_LIMIT_WINDOW = 60

# ============================================================================
# Retry Configuration
# ============================================================================

# Максимальное количество повторных попыток при ошибках
HIKCENTRAL_MAX_RETRIES = 3

# Базовая задержка между попытками (экспоненциально увеличивается)
HIKCENTRAL_RETRY_BASE_DELAY = 1.0

# Максимальная задержка между попытками
HIKCENTRAL_RETRY_MAX_DELAY = 60.0

# ============================================================================
# Connection Pooling Configuration
# ============================================================================

# Количество connection pools для повторного использования соединений
HIKCENTRAL_POOL_CONNECTIONS = 10

# Максимальный размер pool'а соединений
HIKCENTRAL_POOL_MAXSIZE = 20

# ============================================================================
# Timeout Configuration
# ============================================================================

# Таймаут для HTTP запросов в секундах
HIKCENTRAL_TIMEOUT = 30

# ============================================================================
# Async Processing Configuration
# ============================================================================

# Максимальное количество одновременных async операций
HIKCENTRAL_MAX_CONCURRENT = 5

# Порог количества гостей для автоматического переключения на async
HIKCENTRAL_ASYNC_THRESHOLD = 50

# ============================================================================
# Debugging Configuration
# ============================================================================

# Включить отладочные логи для Artemis подписей
HIKCENTRAL_DEBUG_SIGN = False

# Включить подробные метрики производительности
HIKCENTRAL_ENABLE_METRICS = True

# ============================================================================
# Existing Settings (уже были в системе)
# ============================================================================

# Включать ли Date заголовок в подпись
HIKCENTRAL_INCLUDE_DATE = False

# Stage для multi-environment setups
HIKCENTRAL_STAGE = ''

# Организация по умолчанию
HIKCENTRAL_DEFAULT_ORG_INDEX = '1'

# Название организации для автопоиска
HIKCENTRAL_ORG_NAME = ''

# Принудительно использовать организацию из настроек
HIKCENTRAL_FORCE_ORG = False

# ID группы лиц по умолчанию
HIKCENTRAL_FACE_GROUP_INDEX_CODE = ''

# ============================================================================
# Usage Example в settings.py:
# ============================================================================

"""
# HikCentral Professional API Settings
HIKCENTRAL_RATE_LIMIT_CALLS = 15  # 15 calls per minute for production
HIKCENTRAL_RATE_LIMIT_WINDOW = 60
HIKCENTRAL_MAX_RETRIES = 3
HIKCENTRAL_TIMEOUT = 30
HIKCENTRAL_MAX_CONCURRENT = 5
HIKCENTRAL_ASYNC_THRESHOLD = 50
HIKCENTRAL_DEBUG_SIGN = False  # True только для debugging
"""