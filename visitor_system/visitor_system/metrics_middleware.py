from django.utils.deprecation import MiddlewareMixin
import time
import logging

try:
    from prometheus_client import Counter, Histogram, Gauge  # type: ignore
    
    # HTTP метрики
    HTTP_REQUESTS_TOTAL = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )
    
    HTTP_REQUESTS_IN_PROGRESS = Gauge(
        'http_requests_in_progress',
        'HTTP requests currently being processed'
    )
    
    PROMETHEUS_AVAILABLE = True
    
except ImportError:
    PROMETHEUS_AVAILABLE = False
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION_SECONDS = None
    HTTP_REQUESTS_IN_PROGRESS = None

logger = logging.getLogger(__name__)


class PrometheusMetricsMiddleware(MiddlewareMixin):
    """Middleware для сбора HTTP метрик в Prometheus"""
    
    def process_request(self, request):
        if PROMETHEUS_AVAILABLE:
            request._metrics_start_time = time.time()
            HTTP_REQUESTS_IN_PROGRESS.inc()
        return None
    
    def process_response(self, request, response):
        if PROMETHEUS_AVAILABLE and hasattr(request, '_metrics_start_time'):
            # Определяем endpoint
            endpoint = self._get_endpoint(request)
            method = request.method
            status = str(response.status_code)
            
            # Обновляем метрики
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            duration = time.time() - request._metrics_start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            HTTP_REQUESTS_IN_PROGRESS.dec()
        
        return response
    
    def process_exception(self, request, exception):
        if PROMETHEUS_AVAILABLE and hasattr(request, '_metrics_start_time'):
            endpoint = self._get_endpoint(request)
            method = request.method
            
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status='500'
            ).inc()
            
            duration = time.time() - request._metrics_start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            HTTP_REQUESTS_IN_PROGRESS.dec()
        
        return None
    
    def _get_endpoint(self, request):
        """Получает нормализованный endpoint из запроса"""
        path = request.path_info
        
        # Нормализуем пути с ID для группировки метрик
        import re
        
        # Заменяем числовые ID на placeholder
        path = re.sub(r'/\d+/', '/{id}/', path)
        path = re.sub(r'/\d+$', '/{id}', path)
        
        # Заменяем UUID на placeholder
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/',
            '/{uuid}/',
            path,
            flags=re.IGNORECASE
        )
        
        # Заменяем токены на placeholder
        path = re.sub(r'/[a-zA-Z0-9]{32,}/', '/{token}/', path)
        
        return path or '/'
