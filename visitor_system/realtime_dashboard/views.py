from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
try:
    from rest_framework.views import APIView
    from rest_framework.response import Response
    from rest_framework import status
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.throttling import UserRateThrottle
    REST_FRAMEWORK_AVAILABLE = True
except ImportError:
    REST_FRAMEWORK_AVAILABLE = False
import logging

from .services import dashboard_service, event_service
from .models import RealtimeEvent, DashboardWidget

logger = logging.getLogger(__name__)


def _apply_no_store_headers(response):
    """Добавляет заголовки no-store для исключения кеширования ответов API."""
    try:
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
    except Exception:
        # На случай нестандартного объекта ответа просто игнорируем
        pass
    return response


@login_required
def dashboard_view(request):
    """Основная страница дашборда"""
    
    # Получаем активные виджеты для пользователя
    widgets = DashboardWidget.objects.filter(is_active=True).order_by('position_y', 'position_x')
    
    # Если виджетов нет, создаем базовые
    if not widgets.exists():
        _create_default_widgets(request.user)
        widgets = DashboardWidget.objects.filter(is_active=True).order_by('position_y', 'position_x')
    
    context = {
        'widgets': widgets,
        'title': 'Дашборд в реальном времени'
    }
    
    return render(request, 'realtime_dashboard/dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def dashboard_metrics_api(request):
    """API для получения метрик дашборда"""
    try:
        department_id = request.GET.get('department_id')
        period = request.GET.get('period')
        try:
            dep_id_int = int(department_id) if department_id else None
        except ValueError:
            dep_id_int = None
        metrics = dashboard_service.get_current_metrics(department_id=dep_id_int, period=period)
        resp = JsonResponse({
            'success': True,
            'data': metrics,
            'timestamp': metrics['timestamp']
        })
        return _apply_no_store_headers(resp)
    except Exception as e:
        logger.error("Error getting dashboard metrics: %s", e)
        resp = JsonResponse({
            'success': False,
            'error': 'Ошибка получения метрик'
        }, status=500)
        return _apply_no_store_headers(resp)


@login_required
@require_http_methods(["GET"])
def dashboard_events_api(request):
    """API для получения событий в реальном времени"""
    try:
        # Параметры фильтрации/пагинации
        limit = int(request.GET.get('limit', 20))
        page = int(request.GET.get('page', 1))
        event_type = request.GET.get('event_type')
        priority = request.GET.get('priority')
        since = request.GET.get('since')  # ISO-8601 timestamp

        # Базовые события
        events = dashboard_service.get_recent_events(limit=1000)

        # Фильтрация в памяти (упрощённо). Для больших объёмов — перенести в ORM.
        if event_type:
            events = [e for e in events if e.get('type') == event_type]
        if priority:
            events = [e for e in events if e.get('priority') == priority]
        if since:
            try:
                from datetime import datetime
                from django.utils.dateparse import parse_datetime
                since_dt = parse_datetime(since) or datetime.fromisoformat(since)
                events = [e for e in events if e.get('timestamp') and (parse_datetime(e['timestamp']) or datetime.fromisoformat(e['timestamp'])) >= since_dt]
            except Exception:
                pass

        # Пагинация
        total = len(events)
        page_size = max(1, min(100, limit))
        start = (page - 1) * page_size
        end = start + page_size
        page_items = events[start:end]
        
        resp = JsonResponse({
            'success': True,
            'events': page_items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size,
            }
        })
        return _apply_no_store_headers(resp)
    except Exception as e:
        logger.error("Error getting dashboard events: %s", e)
        resp = JsonResponse({
            'success': False,
            'error': 'Ошибка получения событий'
        }, status=500)
        return _apply_no_store_headers(resp)


@login_required
@require_http_methods(["POST"])
def mark_event_read(request, event_id):
    """Отметить событие как прочитанное"""
    try:
        event = RealtimeEvent.objects.get(id=event_id)
        event.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Событие отмечено как прочитанное'
        })
    except RealtimeEvent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Событие не найдено'
        }, status=404)
    except Exception as e:
        logger.error("Error marking event as read: %s", e)
        return JsonResponse({
            'success': False,
            'error': 'Ошибка обновления события'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def widget_data_api(request, widget_id):
    """API для получения данных конкретного виджета"""
    try:
        widget = DashboardWidget.objects.get(id=widget_id, is_active=True)
        
        # Получаем данные в зависимости от типа виджета
        dep_id = request.GET.get('department_id')
        period = request.GET.get('period')
        try:
            dep_id_int = int(dep_id) if dep_id else None
        except ValueError:
            dep_id_int = None
        data = _get_widget_data(widget, department_id=dep_id_int, period=period)
        
        resp = JsonResponse({
            'success': True,
            'widget_id': widget_id,
            'data': data,
            'last_updated': data.get('timestamp')
        })
        return _apply_no_store_headers(resp)
    except DashboardWidget.DoesNotExist:
        resp = JsonResponse({
            'success': False,
            'error': 'Виджет не найден'
        }, status=404)
        return _apply_no_store_headers(resp)
    except Exception as e:
        logger.error("Error getting widget data: %s", e)
        resp = JsonResponse({
            'success': False,
            'error': 'Ошибка получения данных виджета'
        }, status=500)
        return _apply_no_store_headers(resp)


@login_required
@require_http_methods(["GET"])
def active_visits_csv(request):
    """Экспорт CSV активных визитов с учетом фильтров department_id/period"""
    try:
        dep_id = request.GET.get('department_id')
        period = request.GET.get('period')
        try:
            dep_id_int = int(dep_id) if dep_id else None
        except ValueError:
            dep_id_int = None

        metrics = dashboard_service.get_current_metrics(department_id=dep_id_int, period=period)
        active = metrics.get('active_visits', {})
        visits = active.get('visits', [])

        # Формируем CSV (UTF-8 с BOM, разделитель ';', кавычки для безопасного импорта в Excel)
        import io, csv, datetime as _dt
        buf = io.StringIO()
        # Строка для Excel, указываем разделитель
        buf.write('sep=;\n')
        writer = csv.writer(buf, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
        headers = ['id', 'type', 'guest_name', 'department', 'employee', 'entry_time', 'duration_minutes']
        writer.writerow(headers)
        for v in visits:
            writer.writerow([
                v.get('id', ''),
                v.get('type', ''),
                v.get('guest_name', ''),
                v.get('department', ''),
                v.get('employee', ''),
                v.get('entry_time', ''),
                v.get('duration_minutes', 0),
            ])

        # Выбор кодировки (по умолчанию cp1251 для совместимости с Excel на Windows)
        enc = (request.GET.get('encoding') or 'cp1251').lower()
        if enc in ('utf8', 'utf-8', 'utf-8-sig'):
            content = buf.getvalue().encode('utf-8-sig')
            resp_ct = 'text/csv; charset=utf-8'
        else:
            content = buf.getvalue().encode('cp1251', errors='replace')
            resp_ct = 'text/csv; charset=windows-1251'
        filename = f"active_visits_{_dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        resp = HttpResponse(content, content_type=resp_ct)
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return _apply_no_store_headers(resp)
    except Exception as e:
        logger.error("Error exporting CSV: %s", e)
        return _apply_no_store_headers(HttpResponse('Export error', status=500))


# REST API Views (только если доступен REST Framework)
if REST_FRAMEWORK_AVAILABLE:
    class DashboardMetricsAPIView(APIView):
        """REST API для метрик дашборда"""
        permission_classes = [IsAuthenticated]
        throttle_classes = [UserRateThrottle]
        schema = None  # Автосхема от drf-spectacular через DEFAULT_SCHEMA_CLASS
        
        def get(self):
            """Получение всех метрик"""
            try:
                metrics = dashboard_service.get_current_metrics()
                return Response({
                    'success': True,
                    'data': metrics
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error("API error getting metrics: %s", e)
                return Response({
                    'success': False,
                    'error': 'Ошибка получения метрик'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    class RealtimeEventsAPIView(APIView):
        """REST API для событий в реальном времени"""
        permission_classes = [IsAuthenticated]
        throttle_classes = [UserRateThrottle]
        schema = None
        
        def get(self, request):
            """Получение событий"""
            try:
                limit = int(request.query_params.get('limit', 20))
                page = int(request.query_params.get('page', 1))
                event_type = request.query_params.get('event_type')
                priority = request.query_params.get('priority')
                since = request.query_params.get('since')

                events = dashboard_service.get_recent_events(limit=1000)
                if event_type:
                    events = [e for e in events if e.get('type') == event_type]
                if priority:
                    events = [e for e in events if e.get('priority') == priority]
                if since:
                    from datetime import datetime
                    from django.utils.dateparse import parse_datetime
                    try:
                        since_dt = parse_datetime(since) or datetime.fromisoformat(since)
                        events = [e for e in events if e.get('timestamp') and (parse_datetime(e['timestamp']) or datetime.fromisoformat(e['timestamp'])) >= since_dt]
                    except Exception:
                        pass

                total = len(events)
                page_size = max(1, min(100, limit))
                start = (page - 1) * page_size
                end = start + page_size
                page_items = events[start:end]
                
                return Response({
                    'success': True,
                    'events': page_items,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': total,
                        'pages': (total + page_size - 1) // page_size,
                    }
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error("API error getting events: %s", e)
                return Response({
                    'success': False,
                    'error': 'Ошибка получения событий'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        def post(self, request):
            """Создание нового события"""
            try:
                data = request.data
                
                event = event_service.create_event(
                    event_type=data.get('event_type', 'system_alert'),
                    title=data.get('title', ''),
                    message=data.get('message', ''),
                    priority=data.get('priority', 'normal'),
                    user=request.user,
                    data=data.get('data', {})
                )
                
                if event:
                    return Response({
                        'success': True,
                        'event_id': event.id,
                        'message': 'Событие создано'
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'success': False,
                        'error': 'Ошибка создания события'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error("API error creating event: %s", e)
                return Response({
                    'success': False,
                    'error': 'Ошибка создания события'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
else:
    # Заглушки если REST Framework недоступен
    class DashboardMetricsAPIView:
        pass
    
    class RealtimeEventsAPIView:
        pass


def _create_default_widgets(user):
    """Создание виджетов по умолчанию"""
    default_widgets = [
        {
            'name': 'visitors_counter',
            'widget_type': 'counter',
            'title': 'Всего посетителей',
            'position_x': 0, 'position_y': 0,
            'width': 3, 'height': 2,
            'config': {'metric': 'visitors_count', 'color': 'blue'}
        },
        {
            'name': 'active_visits',
            'widget_type': 'counter',
            'title': 'В здании сейчас',
            'position_x': 3, 'position_y': 0,
            'width': 3, 'height': 2,
            'config': {'metric': 'active_visits', 'color': 'green'}
        },
        {
            'name': 'today_registrations',
            'widget_type': 'counter',
            'title': 'Регистраций сегодня',
            'position_x': 6, 'position_y': 0,
            'width': 3, 'height': 2,
            'config': {'metric': 'today_registrations', 'color': 'orange'}
        },
        {
            'name': 'avg_duration',
            'widget_type': 'counter',
            'title': 'Средняя длительность',
            'position_x': 9, 'position_y': 0,
            'width': 3, 'height': 2,
            'config': {'metric': 'avg_visit_duration', 'color': 'purple'}
        },
        {
            'name': 'hourly_chart',
            'widget_type': 'chart_line',
            'title': 'Посещения по часам',
            'position_x': 0, 'position_y': 2,
            'width': 8, 'height': 4,
            'config': {'metric': 'hourly_stats', 'chart_type': 'line'}
        },
        {
            'name': 'department_chart',
            'widget_type': 'chart_pie',
            'title': 'По департаментам',
            'position_x': 8, 'position_y': 2,
            'width': 4, 'height': 4,
            'config': {'metric': 'department_stats', 'chart_type': 'pie'}
        },
        {
            'name': 'recent_events',
            'widget_type': 'activity_feed',
            'title': 'Последние события',
            'position_x': 0, 'position_y': 6,
            'width': 6, 'height': 4,
            'config': {'metric': 'recent_events', 'limit': 10}
        },
        {
            'name': 'active_visits_table',
            'widget_type': 'table',
            'title': 'Активные визиты',
            'position_x': 6, 'position_y': 6,
            'width': 6, 'height': 4,
            'config': {'metric': 'active_visits', 'show_table': True}
        }
    ]
    
    for widget_config in default_widgets:
        DashboardWidget.objects.create(
            created_by=user,
            **widget_config
        )


def _get_widget_data(widget, department_id=None, period=None):
    """Получение данных для виджета"""
    metrics = dashboard_service.get_current_metrics(department_id=department_id, period=period)
    
    metric_name = widget.config.get('metric', '')
    
    if metric_name in metrics:
        return {
            'widget_type': widget.widget_type,
            'data': metrics[metric_name],
            'config': widget.config,
            'timestamp': metrics['timestamp']
        }
    else:
        return {
            'widget_type': widget.widget_type,
            'data': {},
            'config': widget.config,
            'timestamp': metrics['timestamp']
        }
