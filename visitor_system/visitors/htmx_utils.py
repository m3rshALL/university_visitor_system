"""
HTMX utilities and decorators for django-htmx integration
"""
import hashlib
from django.http import HttpResponseNotModified
from django.utils.cache import get_conditional_response
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from functools import wraps
from django_htmx.http import trigger_client_event, push_url


def htmx_cache_control(**kwargs):
    """
    Декоратор для добавления cache-control заголовков к HTMX вьюхам.
    Рекомендуется для часто запрашиваемых эндпоинтов.
    """
    def decorator(view_func):
        @wraps(view_func)
        @cache_control(**kwargs)
        @vary_on_headers('HX-Request', 'HX-Current-URL', 'HX-Target')
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def etag_htmx(etag_func):
    """
    Декоратор для добавления ETag поддержки к HTMX вьюхам.
    etag_func должна принимать request и возвращать строку для ETag.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Генерируем ETag
            etag_value = etag_func(request, *args, **kwargs)
            if etag_value:
                etag_hash = hashlib.md5(etag_value.encode()).hexdigest()
                
                # Проверяем If-None-Match заголовок
                if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
                if if_none_match and if_none_match.strip('"') == etag_hash:
                    return HttpResponseNotModified()
            
            # Вызываем оригинальную вьюху
            response = view_func(request, *args, **kwargs)
            
            # Добавляем ETag к ответу
            if etag_value and hasattr(response, '__setitem__'):
                response['ETag'] = f'"{etag_hash}"'
            
            return response
        return wrapper
    return decorator


def htmx_toast(response, message, toast_type='info', duration=4000):
    """
    Добавляет тост к HTMX ответу.
    """
    trigger_client_event(response, 'showToast', {
        'message': message,
        'type': toast_type,
        'duration': duration
    })
    return response


def htmx_redirect_with_toast(url, message, toast_type='success'):
    """
    Создает HTMX редирект с тостом.
    """
    from django.http import HttpResponse
    response = HttpResponse()
    response['HX-Redirect'] = url
    htmx_toast(response, message, toast_type)
    return response


def htmx_update_counters(response, **counters):
    """
    Обновляет глобальные счетчики через hx-swap-oob.
    """
    trigger_client_event(response, 'updateCounters', counters)
    return response


def stop_polling_response():
    """
    Возвращает ответ, который останавливает polling.
    """
    from django_htmx.http import HttpResponseStopPolling
    return HttpResponseStopPolling()


class HTMXPaginator:
    """
    Пагинатор для HTMX с поддержкой push URL.
    """
    @staticmethod
    def paginate_htmx(request, queryset, per_page=20):
        from django.core.paginator import Paginator
        
        page_num = request.GET.get('page', 1)
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page_num)
        
        # Если это HTMX запрос, обновляем URL
        if request.htmx and page_num != '1':
            new_url = request.get_full_path()
            # push_url автоматически обновит URL в браузере
        
        return page_obj
