"""
Middleware для оптимизации производительности Django-приложения.
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection, reset_queries
from django.conf import settings

logger = logging.getLogger(__name__)

class QueryCountDebugMiddleware(MiddlewareMixin):
    """
    Middleware для подсчета количества SQL запросов для каждого HTTP запроса.
    Полезно для выявления N+1 проблем и оптимизации запросов.
    """
    
    def process_request(self, request):
        if settings.DEBUG:
            # Сбрасываем счетчик запросов
            reset_queries()
            # Сохраняем время начала
            request.start_time = time.time()
    
    def process_response(self, request, response):
        if settings.DEBUG and hasattr(request, 'start_time'):
            # Вычисляем время выполнения
            total_time = time.time() - request.start_time
            # Получаем количество запросов
            total_queries = len(connection.queries)
            
            # Вычисляем время, потраченное на запросы
            query_time = sum([float(q.get('time', 0)) for q in connection.queries])
            
            # Логируем информацию
            logger.debug(f"Path: {request.path}")
            logger.debug(f"Queries: {total_queries}")
            logger.debug(f"Query time: {query_time:.2f}s")
            logger.debug(f"Total time: {total_time:.2f}s")
            
            # Для обнаружения N+1 проблем, логируем запросы, если их слишком много
            if total_queries > 100:  # Порог для запросов
                logger.warning(f"Too many queries ({total_queries}) for {request.path}")
                for i, query in enumerate(connection.queries):
                    logger.debug(f"Query {i}: {query['sql']}")
        
        return response

class ConditionalCacheMiddleware(MiddlewareMixin):
    """
    Middleware для выборочного кэширования ответов на основе правил.
    
    Добавляет кэширование только для определенных URL или типов запросов.
    """
    CACHEABLE_URLS = [
        '/visitors/current/',  # Текущие посетители
        '/visitors/dashboard/employee/',  # Панель управления
        '/visitors/statistics/',  # Статистика
    ]
    
    def process_response(self, request, response):
        """Устанавливает заголовки кэширования для кэшируемых URL."""
        path = request.path
        
        # Если URL в списке кэшируемых и это GET запрос
        if path in self.CACHEABLE_URLS and request.method == 'GET':
            # Устанавливаем Cache-Control
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Приватный кэш для авторизованных пользователей
                response['Cache-Control'] = 'private, max-age=300'  # 5 минут
            else:
                # Публичный кэш для анонимных
                response['Cache-Control'] = 'public, max-age=600'  # 10 минут
        
        # Никогда не кэшируем POST запросы и страницы для авторизованных пользователей, 
        # которые не в списке кэшируемых
        elif request.method == 'POST' or (
            hasattr(request, 'user') and 
            request.user.is_authenticated and 
            path not in self.CACHEABLE_URLS
        ):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        
        return response

class ResourceUsageMiddleware(MiddlewareMixin):
    """
    Middleware для отслеживания использования ресурсов (память, CPU).
    Полезно для выявления утечек памяти и узких мест в производительности.
    """
    
    def process_request(self, request):
        # Начинаем мониторинг ресурсов
        try:
            import resource
            request.resource_start = resource.getrusage(resource.RUSAGE_SELF)
        except ImportError:
            # Не все системы поддерживают модуль resource (например, Windows)
            pass
    
    def process_response(self, request, response):
        if settings.DEBUG and hasattr(request, 'resource_start'):
            try:
                import resource
                resource_end = resource.getrusage(resource.RUSAGE_SELF)
                
                # Вычисляем использование CPU и памяти
                cpu_user = resource_end.ru_utime - request.resource_start.ru_utime
                cpu_system = resource_end.ru_stime - request.resource_start.ru_stime
                mem_increase = resource_end.ru_maxrss - request.resource_start.ru_maxrss
                
                # Логируем, если использование ресурсов превышает пороги
                if cpu_user + cpu_system > 1.0:  # Больше 1 секунды CPU времени
                    logger.warning(f"High CPU usage for {request.path}: User: {cpu_user:.2f}s, System: {cpu_system:.2f}s")
                
                if mem_increase > 10000:  # Больше 10MB памяти (в зависимости от системы единица может быть KB или B)
                    logger.warning(f"High memory usage for {request.path}: {mem_increase} units")
                
            except (ImportError, AttributeError):
                pass
        
        return response
