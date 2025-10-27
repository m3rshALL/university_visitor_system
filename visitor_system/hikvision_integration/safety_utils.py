"""
Утилиты безопасности для предотвращения падения HCP сервера.
"""

import os
import psutil
import logging
import time
from typing import Optional, List, Any
from PIL import Image
from io import BytesIO
from django.core.cache import cache
from .safety_config import *

logger = logging.getLogger(__name__)


def safe_log(level: str, message: str, *args, **kwargs) -> None:
    """Безопасное логирование с ограничением длины сообщения."""
    if not VERBOSE_LOGGING and level == 'DEBUG':
        return
    
    # Ограничиваем длину сообщения
    if len(message) > MAX_LOG_LENGTH:
        message = message[:MAX_LOG_LENGTH] + '...[TRUNCATED]'
    
    # Убираем потенциально большие данные из args
    safe_args = []
    for arg in args:
        if isinstance(arg, (bytes, bytearray)) and len(arg) > 100:
            safe_args.append(f'<{type(arg).__name__}:{len(arg)} bytes>')
        elif isinstance(arg, (dict, list)) and len(str(arg)) > 200:
            safe_args.append(f'<{type(arg).__name__}:{len(arg)} items>')
        else:
            safe_args.append(arg)
    
    getattr(logger, level.lower())(message, *safe_args, **kwargs)


def check_system_resources() -> bool:
    """
    Проверка системных ресурсов перед выполнением задач.
    
    Returns:
        bool: True если ресурсы позволяют выполнять задачи
    """
    if not ENABLE_RESOURCE_MONITORING:
        return True
    
    try:
        # Проверка использования диска
        disk_usage = psutil.disk_usage('/').percent
        if disk_usage > DISK_USAGE_THRESHOLD:
            safe_log('ERROR', 
                f'Disk usage {disk_usage}% exceeds threshold {DISK_USAGE_THRESHOLD}%'
            )
            return False
        
        # Проверка использования памяти
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > MEMORY_USAGE_THRESHOLD:
            safe_log('ERROR',
                f'Memory usage {memory_usage}% exceeds threshold {MEMORY_USAGE_THRESHOLD}%'
            )
            return False
        
        return True
        
    except Exception as e:
        safe_log('WARNING', f'Failed to check system resources: {e}')
        return True  # Продолжаем работу при ошибке проверки


def validate_image_safely(image_bytes: bytes) -> tuple[bool, Optional[str]]:
    """
    Безопасная валидация изображения.
    
    Args:
        image_bytes: Байты изображения
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not image_bytes:
        return False, "Empty image data"
    
    # Проверка размера
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        return False, f"Image too large: {len(image_bytes)} bytes > {MAX_IMAGE_SIZE_BYTES}"
    
    # Проверка формата
    try:
        with BytesIO(image_bytes) as img_buffer:
            with Image.open(img_buffer) as img:
                if img.format not in ALLOWED_IMAGE_FORMATS:
                    return False, f"Unsupported format: {img.format}"
                
                # Проверка разумных размеров
                width, height = img.size
                if width > 4000 or height > 4000:
                    return False, f"Image dimensions too large: {width}x{height}"
                
                if width < 50 or height < 50:
                    return False, f"Image dimensions too small: {width}x{height}"
                
        return True, None
        
    except Exception as e:
        return False, f"Invalid image format: {e}"


def safe_read_file(file_path: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    Безопасное чтение файла с проверками.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        tuple: (file_bytes, error_message)
    """
    try:
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
        
        # Проверка размера файла
        file_size = os.path.getsize(file_path)
        if file_size > MAX_IMAGE_SIZE_BYTES:
            return None, f"File too large: {file_size} bytes"
        
        if file_size == 0:
            return None, "Empty file"
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return data, None
        
    except Exception as e:
        return None, f"Failed to read file: {e}"


def get_monitoring_cache_key(visit_id: int) -> str:
    """Ключ кэша для мониторинга визита."""
    return f"monitoring_visit_{visit_id}"


def should_monitor_visit(visit_id: int) -> bool:
    """
    Проверка, нужно ли мониторить визит (с учетом rate limiting).
    
    Args:
        visit_id: ID визита
        
    Returns:
        bool: True если можно мониторить
    """
    cache_key = get_monitoring_cache_key(visit_id)
    
    if cache.get(cache_key):
        return False  # Недавно уже проверяли
    
    # Устанавливаем блокировку
    cache.set(cache_key, True, MONITORING_RATE_LIMIT_SECONDS)
    return True


def chunk_list(data: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Разбивка списка на безопасные куски.
    
    Args:
        data: Исходный список
        chunk_size: Размер куска
        
    Returns:
        List: Список кусков
    """
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunks.append(data[i:i + chunk_size])
    return chunks


def safe_batch_operation(operation_name: str, items: List[Any], 
                        max_batch_size: int = MAX_BATCH_SIZE) -> List[List[Any]]:
    """
    Безопасная подготовка batch операции.
    
    Args:
        operation_name: Название операции
        items: Список элементов
        max_batch_size: Максимальный размер batch
        
    Returns:
        List: Безопасные куски для обработки
    """
    if not check_system_resources():
        safe_log('ERROR', f'System resources exhausted, skipping {operation_name}')
        return []
    
    if len(items) > max_batch_size:
        safe_log('WARNING', 
            f'{operation_name}: Large batch {len(items)} items, splitting into chunks'
        )
        return chunk_list(items, max_batch_size)
    
    return [items]


def cleanup_memory():
    """Принудительная очистка памяти после тяжелых операций."""
    import gc
    gc.collect()


class SafeOperationContext:
    """Контекстный менеджер для безопасных операций."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        if not check_system_resources():
            raise RuntimeError(f'System resources exhausted for {self.operation_name}')
        
        self.start_time = time.time()
        safe_log('INFO', f'{self.operation_name}: Operation started')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            safe_log('ERROR', f'{self.operation_name}: Failed after {duration:.2f}s: {exc_val}')
        else:
            safe_log('INFO', f'{self.operation_name}: Completed in {duration:.2f}s')
        
        cleanup_memory()
        
        if duration > OPERATION_TIMEOUT_SECONDS:
            safe_log('WARNING', f'{self.operation_name}: Operation took too long: {duration:.2f}s')


def get_safe_visit_batch_for_monitoring(limit: int = MAX_CONCURRENT_MONITORING) -> List[int]:
    """
    Получает безопасную batch визитов для мониторинга.
    
    Args:
        limit: Максимальное количество визитов
        
    Returns:
        List[int]: ID визитов для мониторинга
    """
    from visitors.models import Visit
    
    # Получаем только те визиты, которые можно мониторить
    visits = Visit.objects.filter(
        access_granted=True,
        access_revoked=False,
        status__in=['EXPECTED', 'CHECKED_IN']
    ).values_list('id', flat=True)[:limit * 2]  # Берем больше для фильтрации
    
    # Фильтруем по rate limiting
    safe_visits = []
    for visit_id in visits:
        if should_monitor_visit(visit_id) and len(safe_visits) < limit:
            safe_visits.append(visit_id)
    
    return safe_visits


import time