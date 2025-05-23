from django import template
from django.core.cache import cache
from django.utils.safestring import mark_safe
import hashlib
import json

register = template.Library()

@register.simple_tag(takes_context=True)
def cached_template_block(context, fragment_name, *args, timeout=300):
    """
    Кэширует часть шаблона на основе имени и аргументов.
    Учитывает текущего пользователя для приватного кэширования.
    
    """
    request = context.get('request')
    user_id = request.user.id if request and request.user.is_authenticated else None
    
    # Создаем хэш-ключ, содержащий имя фрагмента, аргументы и ID пользователя
    args_str = '-'.join([str(arg) for arg in args])
    cache_key = f"template_cache:{fragment_name}:{args_str}:user_{user_id}"
    
    # Проверяем кэш
    content = cache.get(cache_key)
    if content is not None:
        return mark_safe(content)
    
    # Если нет в кэше, выполняем блок шаблона
    nodelist = context.get('nodelist')
    if nodelist:
        content = nodelist.render(context)
        cache.set(cache_key, content, timeout)
        return mark_safe(content)
    
    return ''

@register.simple_tag
def cached_queryset(queryset, cache_key, timeout=300):
    """
    Кэширует результат QuerySet и возвращает его.
    
    """
    cached_result = cache.get(cache_key)
    if cached_result is None:
        cached_result = list(queryset)
        cache.set(cache_key, cached_result, timeout)
    return cached_result

@register.filter
def json_script_cached(value, element_id):
    """
    Улучшенная версия json_script с кэшированием для улучшения производительности.
    """
    cache_key = f"json_script:{element_id}:{hash(str(value))}"
    cached_output = cache.get(cache_key)
    
    if cached_output is None:
        json_str = json.dumps(value)
        cached_output = f'<script id="{element_id}" type="application/json">{json_str}</script>'
        cache.set(cache_key, cached_output, 3600)  # Кэшируем на 1 час
    
    return mark_safe(cached_output)
