"""
Rate Limiter для HikCentral Professional API.

Предотвращает перегрузку HCP сервера при массовых запросах.
Использует sliding window алгоритм для контроля частоты вызовов API.
"""
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter с sliding window алгоритмом.
    
    Ограничивает количество вызовов в заданный временной промежуток.
    Автоматически блокирует выполнение при превышении лимита.
    
    Args:
        calls_per_window: Максимальное количество вызовов за окно
        window_seconds: Размер временного окна в секундах
        
    Example:
        >>> limiter = RateLimiter(calls_per_window=10, window_seconds=60)
        >>> limiter.acquire()  # Блокирует если превышен лимит
        >>> # Выполнить API запрос
    """
    
    def __init__(self, calls_per_window: int, window_seconds: int):
        self.calls = calls_per_window
        self.window = window_seconds
        self.timestamps = []
        self.lock = Lock()
        self.total_waits = 0
        self.total_requests = 0
        
        logger.info(
            "RateLimiter initialized: %d calls per %d seconds",
            calls_per_window, window_seconds
        )
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Получает разрешение на выполнение запроса.
        
        Args:
            blocking: Если True - блокирует до получения разрешения,
                     Если False - сразу возвращает True/False
                     
        Returns:
            True если разрешение получено, False если лимит превышен (только при blocking=False)
        """
        with self.lock:
            now = time.time()
            
            # Удаляем timestamps старше окна
            self.timestamps = [t for t in self.timestamps if now - t < self.window]
            
            if len(self.timestamps) >= self.calls:
                if not blocking:
                    return False
                
                # Вычисляем время ожидания
                oldest_timestamp = self.timestamps[0]
                sleep_time = self.window - (now - oldest_timestamp)
                
                if sleep_time > 0:
                    self.total_waits += 1
                    logger.warning(
                        "Rate limit reached (%d/%d calls), sleeping %.2f seconds",
                        len(self.timestamps), self.calls, sleep_time
                    )
                    # Освобождаем lock на время сна
                    self.lock.release()
                    try:
                        time.sleep(sleep_time)
                    finally:
                        self.lock.acquire()
                    
                    # Рекурсивно пытаемся снова
                    return self.acquire(blocking=blocking)
            
            # Добавляем текущий timestamp
            self.timestamps.append(now)
            self.total_requests += 1
            return True
    
    def reset(self):
        """Сбрасывает счетчики (для тестирования)."""
        with self.lock:
            self.timestamps = []
            self.total_waits = 0
            self.total_requests = 0
            logger.info("RateLimiter reset")
    
    def get_stats(self) -> dict:
        """
        Возвращает статистику использования.
        
        Returns:
            dict с полями: total_requests, total_waits, current_window_count
        """
        with self.lock:
            now = time.time()
            current_count = len([t for t in self.timestamps if now - t < self.window])
            
            return {
                'total_requests': self.total_requests,
                'total_waits': self.total_waits,
                'current_window_count': current_count,
                'limit': self.calls,
                'window_seconds': self.window,
            }


# Глобальный rate limiter для HikCentral Professional API
# По умолчанию: 10 запросов за 60 секунд
# Можно переопределить через settings.HIKCENTRAL_RATE_LIMIT_*
hcp_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(calls_per_window: int = 10, window_seconds: int = 60) -> RateLimiter:
    """
    Получает глобальный rate limiter (singleton).
    
    Args:
        calls_per_window: Лимит вызовов (используется только при первом создании)
        window_seconds: Размер окна в секундах (используется только при первом создании)
        
    Returns:
        Глобальный RateLimiter instance
    """
    global hcp_rate_limiter
    
    if hcp_rate_limiter is None:
        # Пытаемся получить из settings
        try:
            from django.conf import settings
            calls = getattr(settings, 'HIKCENTRAL_RATE_LIMIT_CALLS', calls_per_window)
            window = getattr(settings, 'HIKCENTRAL_RATE_LIMIT_WINDOW', window_seconds)
            hcp_rate_limiter = RateLimiter(calls_per_window=calls, window_seconds=window)
        except Exception as e:
            logger.warning("Failed to load rate limit from settings: %s, using defaults", e)
            hcp_rate_limiter = RateLimiter(
                calls_per_window=calls_per_window,
                window_seconds=window_seconds
            )
    
    return hcp_rate_limiter

