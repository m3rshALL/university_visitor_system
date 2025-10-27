"""
Примеры использования оптимизированных HikCentral API методов.

Этот файл содержит примеры того, как использовать новые оптимизации:
- Rate limiting
- Batch operations  
- Async processing
- Monitoring
"""

from datetime import datetime, timedelta
from django.conf import settings
from .services import (
    HikCentralSession, 
    process_multiple_guests,
    batch_reapply_access,
    batch_assign_access_levels
)
from .models import HikCentralServer


def example_single_guest_with_monitoring():
    """Пример обработки одного гостя с мониторингом производительности."""
    
    # Получаем сервер из базы
    server = HikCentralServer.objects.first()
    
    # Создаем сессию с настройками rate limiting
    session = HikCentralSession(
        server=server,
        rate_limit_calls=10,  # 10 вызовов
        rate_limit_window=60  # за 60 секунд
    )
    
    try:
        # Обрабатываем гостя (автоматически применяется rate limiting)
        from .services import ensure_person_hikcentral, upload_face_hikcentral
        
        person_id = ensure_person_hikcentral(
            session, 
            employee_no="GUEST001",
            name="Иван Иванов",
            valid_from=datetime.now().isoformat(),
            valid_to=(datetime.now() + timedelta(days=1)).isoformat()
        )
        
        # Загружаем фото (если есть)
        with open("photo.jpg", "rb") as f:
            image_bytes = f.read()
            face_result = upload_face_hikcentral(session, "", image_bytes, person_id)
        
        print(f"Гость создан: person_id={person_id}, face={face_result}")
        
    finally:
        # Получаем и логируем метрики
        metrics = session.get_metrics()
        print(f"Статистика API: {metrics}")
        session.log_metrics_summary()


def example_batch_processing_sync():
    """Пример синхронной batch обработки 20 гостей."""
    
    server = HikCentralServer.objects.first()
    session = HikCentralSession(server)
    
    # Подготавливаем данные гостей
    guests_data = []
    for i in range(20):
        guests_data.append({
            'employee_no': f'GUEST{i:03d}',
            'name': f'Гость {i+1}',
            'valid_from': datetime.now().isoformat(),
            'valid_to': (datetime.now() + timedelta(days=1)).isoformat(),
            # 'image_bytes': load_photo_bytes(f'guest_{i}.jpg')  # если есть фото
        })
    
    # Обрабатываем синхронно с batch access assignment
    result = process_multiple_guests(
        session=session,
        guests_data=guests_data,
        use_async=False,  # Принудительно sync
        batch_access_group="123"  # ID группы доступа для всех гостей
    )
    
    print(f"Результат batch обработки: {result}")


def example_async_processing_large_batch():
    """Пример асинхронной обработки 100+ гостей."""
    
    server = HikCentralServer.objects.first()
    session = HikCentralSession(server)
    
    # Подготавливаем данные большой группы гостей
    guests_data = []
    for i in range(100):
        guests_data.append({
            'employee_no': f'EVENT_GUEST_{i:04d}',
            'name': f'Участник мероприятия {i+1}',
            'valid_from': datetime.now().isoformat(),
            'valid_to': (datetime.now() + timedelta(hours=8)).isoformat(),
        })
    
    # Автоматически выберет async (100 > 50)
    result = process_multiple_guests(
        session=session,
        guests_data=guests_data,
        use_async=None,  # Автоматический выбор
        batch_access_group="456"  # Группа доступа для мероприятия
    )
    
    print(f"Async обработка завершена за {result['duration_seconds']}s")
    print(f"Производительность: {result['guests_per_second']} гостей/сек")


def example_manual_batch_operations():
    """Пример ручного использования batch операций."""
    
    server = HikCentralServer.objects.first()
    session = HikCentralSession(server)
    
    # Предположим у нас есть список person_ids
    person_ids = ["1001", "1002", "1003", "1004", "1005"]
    access_group_id = "789"
    
    # Batch назначение доступа
    success = batch_assign_access_levels(
        session=session,
        person_ids=person_ids,
        access_group_id=access_group_id,
        access_type=1  # Access control
    )
    
    if success:
        print(f"Доступ назначен для {len(person_ids)} персон")
    else:
        print("Ошибка batch назначения доступа")
    
    # Отдельный batch reapply если нужно
    batch_reapply_access(session, person_ids)


def example_error_handling_and_retry():
    """Пример обработки ошибок с автоматическими повторами."""
    
    server = HikCentralServer.objects.first()
    session = HikCentralSession(server)
    
    try:
        # Этот запрос автоматически повторится при временных ошибках
        from .services import find_org_by_name
        
        org_id = find_org_by_name(session, "Тестовая организация")
        print(f"Найдена организация: {org_id}")
        
    except Exception as e:
        # Окончательная ошибка после всех повторов
        print(f"Запрос провалился после всех попыток: {e}")
        
        # Можем посмотреть метрики для анализа
        metrics = session.get_metrics()
        print(f"Статистика ошибок: {metrics['error_count']}/{metrics['total_calls']}")


def example_monitoring_dashboard():
    """Пример создания dashboard'а для мониторинга API."""
    
    server = HikCentralServer.objects.first()
    session = HikCentralSession(server)
    
    # После выполнения операций получаем детальную статистику
    metrics = session.get_metrics()
    
    dashboard_data = {
        'api_health': {
            'total_calls': metrics['total_calls'],
            'error_rate': metrics['error_rate'],
            'average_response_time': metrics['average_time']
        },
        'performance': {
            'total_time': metrics['total_time'],
            'calls_per_second': metrics['total_calls'] / max(metrics['total_time'], 1)
        },
        'endpoints': {
            endpoint: {
                'calls': stats['count'],
                'avg_time': stats['time'] / max(stats['count'], 1),
                'error_rate': (stats['errors'] / max(stats['count'], 1)) * 100
            }
            for endpoint, stats in metrics['endpoints'].items()
        }
    }
    
    print("=== HikCentral API Dashboard ===")
    print(f"Всего вызовов: {dashboard_data['api_health']['total_calls']}")
    print(f"Частота ошибок: {dashboard_data['api_health']['error_rate']:.1f}%")
    print(f"Среднее время ответа: {dashboard_data['api_health']['average_response_time']:.3f}s")
    print(f"Производительность: {dashboard_data['performance']['calls_per_second']:.1f} calls/s")
    
    return dashboard_data


# ============================================================================
# Integration Examples для использования в Django Views
# ============================================================================

def django_view_example(request):
    """Пример использования в Django view."""
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    
    @require_http_methods(["POST"])
    def register_multiple_guests(request):
        import json
        
        # Получаем данные гостей из request
        guests_data = json.loads(request.body)
        
        # Обрабатываем через оптимизированный API
        server = HikCentralServer.objects.first()
        session = HikCentralSession(server)
        
        try:
            result = process_multiple_guests(
                session=session,
                guests_data=guests_data,
                batch_access_group=request.POST.get('access_group_id')
            )
            
            return JsonResponse({
                'success': True,
                'result': result,
                'api_metrics': session.get_metrics()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'api_metrics': session.get_metrics()
            }, status=500)


def celery_task_example():
    """Пример использования в Celery task для фоновой обработки."""
    from celery import shared_task
    
    @shared_task
    def process_guest_batch_async(guests_data, access_group_id=None):
        """Celery task для асинхронной обработки гостей."""
        
        server = HikCentralServer.objects.first()
        session = HikCentralSession(server)
        
        try:
            result = process_multiple_guests(
                session=session,
                guests_data=guests_data,
                use_async=True,  # Используем async внутри task
                batch_access_group=access_group_id
            )
            
            # Логируем результат
            session.log_metrics_summary()
            
            return {
                'success': True,
                'processed': result['successful'],
                'failed': result['failed'],
                'duration': result['duration_seconds']
            }
            
        except Exception as e:
            logger.error(f"Celery task failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


if __name__ == "__main__":
    # Запуск примеров для тестирования
    print("Тестирование оптимизированного HikCentral API...")
    
    # example_single_guest_with_monitoring()
    # example_batch_processing_sync() 
    # example_async_processing_large_batch()
    # example_manual_batch_operations()
    # example_monitoring_dashboard()
    
    print("Примеры готовы к использованию!")