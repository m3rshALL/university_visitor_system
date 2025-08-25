"""
Оптимизированные настройки и утилиты для работы с Redis кэшем.
"""
from django.core.cache import cache
from django_redis import get_redis_connection
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def optimized_cache_get(key, default=None, version=None, retry_count=3, retry_delay=0.1):
    """
    Оптимизированная функция получения значения из кэша с повторными попытками при сбоях.
    
    Args:
        key: Ключ кэша
        default: Значение по умолчанию, если ключ не найден
        version: Версия кэша
        retry_count: Количество повторных попыток
        retry_delay: Задержка между попытками в секундах
        
    Returns:
        Значение из кэша или default
    """
    for attempt in range(retry_count):
        try:
            return cache.get(key, default, version)
        except Exception as e:
            if attempt == retry_count - 1:
                logger.error(f"Failed to get from cache after {retry_count} attempts: {e}")
                return default
            logger.warning(f"Cache get error (attempt {attempt+1}/{retry_count}): {e}")
            time.sleep(retry_delay)
    return default

def optimized_cache_set(key, value, timeout=None, version=None, retry_count=3, retry_delay=0.1):
    """
    Оптимизированная функция сохранения значения в кэш с повторными попытками при сбоях.
    
    Args:
        key: Ключ кэша
        value: Значение для сохранения
        timeout: Время жизни в секундах
        version: Версия кэша
        retry_count: Количество повторных попыток
        retry_delay: Задержка между попытками в секундах
        
    Returns:
        True если успешно, False если нет
    """
    for attempt in range(retry_count):
        try:
            return cache.set(key, value, timeout, version)
        except Exception as e:
            if attempt == retry_count - 1:
                logger.error(f"Failed to set cache after {retry_count} attempts: {e}")
                return False
            logger.warning(f"Cache set error (attempt {attempt+1}/{retry_count}): {e}")
            time.sleep(retry_delay)
    return False

def get_redis_client():
    """
    Получение напрямую клиента Redis для более эффективных групповых операций.
    
    Returns:
        Клиент Redis
    """
    try:
        return get_redis_connection("default")
    except Exception as e:
        logger.error(f"Failed to get Redis connection: {e}")
        return None

def redis_pipeline_decorator(func=None, ttl=300):
    """
    Декоратор для использования Redis pipeline для групповых операций.
    Значительно ускоряет операции с большим количеством ключей.
    
    Args:
        func: Декорируемая функция
        ttl: Время жизни кэша в секундах
        
    Returns:
        Декорированная функция
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Получаем Redis клиент и создаем pipeline
            client = get_redis_client()
            if not client:
                # Если невозможно получить клиент, выполняем функцию без кэширования
                return f(*args, **kwargs)
                
            pipeline = client.pipeline()
            
            # Вызываем функцию, предполагая что она будет использовать pipeline
            kwargs['redis_pipeline'] = pipeline
            result = f(*args, **kwargs)
            
            # Выполняем все команды за один раз
            try:
                pipeline.execute()
            except Exception as e:
                logger.error(f"Redis pipeline error: {e}")
                
            return result
        return wrapper
    
    if func:
        return decorator(func)
    return decorator

def optimize_redis_connection():
    """
    Оптимизирует текущие настройки соединения с Redis в проекте.
    Вызывайте при запуске приложения.
    """
    try:
        client = get_redis_client()
        if client:
            # Устанавливаем оптимальные настройки для TCP
            client.connection_pool.connection_kwargs.update({
                'socket_keepalive': True,
                'retry_on_timeout': True,
                'health_check_interval': 30,  # Проверка соединения каждые 30 секунд
            })
            logger.info("Redis connection optimized successfully")
        else:
            logger.warning("Could not optimize Redis connection - client not available")
    except Exception as e:
        logger.error("Failed to optimize Redis connection: %s", e)

class RedisBatchCache:
    """
    Класс для эффективных групповых операций с кэшем.
    Особенно полезно для страниц с большим количеством кэшированных фрагментов.
    """
    
    def __init__(self):
        self.client = get_redis_client()
        self.pipeline = self.client.pipeline() if self.client else None
        
    def mget(self, keys):
        """
        Получение нескольких значений за раз.
        
        Args:
            keys: Список ключей
            
        Returns:
            Словарь {ключ: значение}
        """
        if not self.client or not keys:
            return {}
        
        try:
            # Получаем все значения за один запрос
            values = self.client.mget(keys)
            return dict(zip(keys, values))
        except Exception as e:
            logger.error("Redis mget error: %s", e)
            return {}
            
    def mset(self, mapping, ttl=300):
        """
        Установка нескольких значений за раз.
        
        Args:
            mapping: Словарь {ключ: значение}
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно, False если нет
        """
        if not self.client or not mapping:
            return False
            
        try:
            # Используем pipeline для атомарной установки всех значений
            pipe = self.client.pipeline()
            pipe.mset(mapping)
            
            # Устанавливаем TTL для каждого ключа
            for key in mapping.keys():
                pipe.expire(key, ttl)
                
            pipe.execute()
            return True
        except Exception as e:
            logger.error("Redis mset error: %s", e)
            return False
