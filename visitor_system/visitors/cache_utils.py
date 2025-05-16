from django.core.cache import cache
from django.utils.functional import wraps
from django.db.models import Model, QuerySet
import hashlib
import inspect
import functools
import json
import logging

logger = logging.getLogger(__name__)

def cached_function(timeout=300, prefix='cached_func'):
    """
    Декоратор для кэширования результатов функции.
    
    Пример использования:
    @cached_function(timeout=600, prefix='my_app')
    def expensive_calculation(arg1, arg2):
        # ...сложные вычисления...
        return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ кэша из имени функции, аргументов и именованных аргументов
            func_name = func.__name__
            # Преобразуем args в строку, обрабатывая специальные случаи
            args_str = []
            for arg in args:
                if isinstance(arg, Model):
                    # Для моделей используем pk или id
                    args_str.append(f"{arg.__class__.__name__}_{getattr(arg, 'pk', getattr(arg, 'id', id(arg)))}")
                elif isinstance(arg, QuerySet):
                    # Для QuerySet используем SQL запрос
                    args_str.append(f"qs_{hash(str(arg.query))}")
                else:
                    args_str.append(str(arg))
            
            # Форматируем kwargs
            kwargs_str = []
            for k, v in sorted(kwargs.items()):
                if isinstance(v, Model):
                    kwargs_str.append(f"{k}={v.__class__.__name__}_{getattr(v, 'pk', getattr(v, 'id', id(v)))}")
                elif isinstance(v, QuerySet):
                    kwargs_str.append(f"{k}=qs_{hash(str(v.query))}")
                else:
                    kwargs_str.append(f"{k}={v}")
            
            # Создаем хэш-ключ
            key_parts = [prefix, func_name, '_'.join(args_str), '_'.join(kwargs_str)]
            key = hashlib.md5('_'.join(key_parts).encode()).hexdigest()
            
            # Проверяем кэш
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name} with key {key}")
                return cached_result
            
            # Если не в кэше, вычисляем и сохраняем
            logger.debug(f"Cache miss for {func_name}, computing result")
            result = func(*args, **kwargs)
            cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator

def cached_property_with_ttl(ttl=None):
    """
    Декоратор, похожий на @cached_property, но с возможностью указать время жизни кэша.
    
    Пример использования:
    class MyModel(models.Model):
        @cached_property_with_ttl(ttl=300)  # 5 минут
        def expensive_calculation(self):
            # ... сложные вычисления ...
            return result
    """
    def decorator(method):
        cache_name = f"_ttl_cache_{method.__name__}"
        
        @property
        def wrapper(self):
            # Проверяем наличие кэша и его актуальность
            cache_info = getattr(self, cache_name, None)
            
            # Если кэш есть и не просрочен, возвращаем результат
            if cache_info is not None:
                value, expire_time = cache_info
                if expire_time is None or time.time() < expire_time:
                    return value
            
            # Вычисляем результат
            value = method(self)
            
            # Сохраняем результат и время истечения (если ttl указан)
            expire_time = time.time() + ttl if ttl is not None else None
            setattr(self, cache_name, (value, expire_time))
            
            return value
        return wrapper
    return decorator

def bust_model_cache(model_instance):
    """
    Инвалидирует кэш, связанный с конкретным объектом модели.
    
    Пример использования:
    @receiver(post_save, sender=Visit)
    def clear_visit_cache(sender, instance, **kwargs):
        bust_model_cache(instance)
    """
    # Генерируем префикс ключа кэша для этой модели
    model_name = model_instance.__class__.__name__
    model_id = getattr(model_instance, 'pk', getattr(model_instance, 'id', id(model_instance)))
    cache_key_prefix = f"{model_name}_{model_id}"
    
    # Логирование
    logger.debug(f"Busting cache for {model_name} with ID {model_id}")
    
    # Для Redis можно использовать паттерн-удаление
    try:
        # Получаем клиент Redis
        from django_redis import get_redis_connection
        client = get_redis_connection("default")
        
        # Удаляем ключи по шаблону
        keys = client.keys(f"*{cache_key_prefix}*")
        if keys:
            client.delete(*keys)
            logger.debug(f"Deleted {len(keys)} cache keys for {model_name}_{model_id}")
    except Exception as e:
        logger.error(f"Error clearing Redis cache: {e}")
        
        # Фоллбэк: инвалидируем весь кэш
        cache.clear()
        logger.warning("Fallback: cleared entire cache due to Redis error")
