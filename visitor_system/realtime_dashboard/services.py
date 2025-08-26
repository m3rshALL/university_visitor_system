from django.db.models import Count
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from visitors.models import Visit, StudentVisit, Guest
from departments.models import Department
from .models import DashboardMetric, RealtimeEvent
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
try:
    from prometheus_client import Gauge  # type: ignore
    ACTIVE_VISITS_GAUGE = Gauge('active_visits_total', 'Active visits in building')
    NO_SHOW_GAUGE = Gauge('no_show_total', 'No-show planned visits (past expected, never checked-in)')
    AVG_VISIT_DURATION_MIN = Gauge('avg_visit_duration_minutes', 'Average visit duration (completed)')
except Exception:
    ACTIVE_VISITS_GAUGE = None
    NO_SHOW_GAUGE = None
    AVG_VISIT_DURATION_MIN = None

logger = logging.getLogger(__name__)


class DashboardMetricsService:
    """
    Сервис для сбора и обновления метрик дашборда
    """
    
    def get_current_metrics(self, department_id: int | None = None, period: str | None = None):
        """Получение текущих метрик с учётом фильтров"""
        now = timezone.now()
        # P1: короткий кеш на 5-10 секунд, ключ учитывает фильтры
        cache_key = f"dash:metrics:dep={department_id or 'all'}:period={(period or '24h').lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        period = (period or '24h').lower()

        # Определяем временную границу
        if period == 'today':
            start_dt = timezone.make_aware(datetime.combine(now.date(), datetime.min.time()))
        elif period in ('24h', '1d'):
            start_dt = now - timedelta(hours=24)
        elif period in ('7d', 'week'):
            start_dt = now - timedelta(days=7)
        elif period in ('30d', 'month'):
            start_dt = now - timedelta(days=30)
        else:
            start_dt = now - timedelta(hours=24)

        metrics = {
            'visitors_count': self.get_visitors_count(start_dt=start_dt),
            'active_visits': self.get_active_visits(department_id=department_id),
            'today_registrations': self.get_today_registrations(start_dt=start_dt),
            'avg_visit_duration': self.get_avg_visit_duration(start_dt=start_dt),
            'department_stats': self.get_department_stats(),
            'hourly_stats': self.get_hourly_stats(),
            'recent_events': self.get_recent_events(),
            'security_alerts': self.get_security_alerts(),
            'timestamp': now.isoformat()
        }

        # Короткое кеширование
        cache.set(cache_key, metrics, timeout=10)
        return metrics
    
    def get_visitors_count(self, start_dt: datetime | None = None):
        """Общее количество посетителей"""
        qs_v = Visit.objects.all()
        qs_sv = StudentVisit.objects.all()
        if start_dt:
            qs_v = qs_v.filter(entry_time__gte=start_dt)
            qs_sv = qs_sv.filter(entry_time__gte=start_dt)
        total_visits = qs_v.count()
        total_student_visits = qs_sv.count()
        unique_guests = Guest.objects.count()
        
        return {
            'total_visits': total_visits,
            'total_student_visits': total_student_visits,
            'unique_guests': unique_guests,
            'total_all': total_visits + total_student_visits
        }
    
    def get_active_visits(self, department_id: int | None = None):
        """Активные визиты (в здании)"""
        v_filter = {
            'status': 'CHECKED_IN',
            'exit_time__isnull': True,
        }
        if department_id:
            v_filter['department_id'] = department_id
        active_visits = Visit.objects.filter(
            **v_filter
        ).select_related('guest', 'department', 'employee')
        
        sv_filter = {
            'status': 'CHECKED_IN',
            'exit_time__isnull': True,
        }
        if department_id:
            sv_filter['department_id'] = department_id
        active_student_visits = StudentVisit.objects.filter(
            **sv_filter
        ).select_related('guest', 'department')
        
        # Формируем данные для отображения
        visits_data = []
        
        for visit in active_visits:
            visits_data.append({
                'id': visit.id,
                'type': 'official',
                'guest_name': visit.guest.full_name,
                'department': visit.department.name,
                'employee': visit.employee.get_full_name(),
                'entry_time': visit.entry_time.isoformat() if visit.entry_time else None,
                'duration_minutes': self.calculate_duration_minutes(visit.entry_time) if visit.entry_time else 0
            })
        
        for visit in active_student_visits:
            visits_data.append({
                'id': visit.id,
                'type': 'student',
                'guest_name': visit.guest.full_name,
                'department': visit.department.name,
                'entry_time': visit.entry_time.isoformat() if visit.entry_time else None,
                'duration_minutes': self.calculate_duration_minutes(visit.entry_time) if visit.entry_time else 0
            })
        
        result = {
            'count': len(visits_data),
            'official_count': active_visits.count(),
            'student_count': active_student_visits.count(),
            'visits': visits_data
        }
        try:
            if ACTIVE_VISITS_GAUGE:
                ACTIVE_VISITS_GAUGE.set(result['count'])
        except Exception:
            pass
        return result
    
    def get_today_registrations(self, start_dt: datetime | None = None):
        """Регистрации за сегодня"""
        now = timezone.now()
        if start_dt is None:
            start_dt = timezone.make_aware(datetime.combine(now.date(), datetime.min.time()))
        # День, по которому строим часовую разбивку
        today = (start_dt or now).date()
        
        today_visits = Visit.objects.filter(entry_time__gte=start_dt).count()
        today_student_visits = StudentVisit.objects.filter(entry_time__gte=start_dt).count()
        
        # Почасовая статистика за сегодня
        hourly_data = []
        # Старт дня (aware)
        day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        for hour in range(24):
            hour_start = day_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            visits_count = Visit.objects.filter(
                entry_time__gte=hour_start,
                entry_time__lt=hour_end
            ).count()
            
            student_visits_count = StudentVisit.objects.filter(
                entry_time__gte=hour_start,
                entry_time__lt=hour_end
            ).count()
            
            hourly_data.append({
                'hour': hour_start.strftime('%H:00'),
                'visits': visits_count,
                'student_visits': student_visits_count,
                'total': visits_count + student_visits_count
            })
        
        return {
            'total_today': today_visits + today_student_visits,
            'official_today': today_visits,
            'student_today': today_student_visits,
            'hourly_data': hourly_data
        }
    
    def get_avg_visit_duration(self, start_dt: datetime | None = None):
        """Средняя длительность визитов"""
        # Завершенные визиты за период (по умолчанию 30 дней)
        thirty_days_ago = start_dt or (timezone.now() - timedelta(days=30))
        
        completed_visits = Visit.objects.filter(
            entry_time__gte=thirty_days_ago,
            exit_time__isnull=False
        )
        
        completed_student_visits = StudentVisit.objects.filter(
            entry_time__gte=thirty_days_ago,
            exit_time__isnull=False
        )
        
        # Вычисляем среднюю длительность
        total_duration_minutes = 0
        total_count = 0
        
        for visit in completed_visits:
            if visit.entry_time and visit.exit_time:
                duration = visit.exit_time - visit.entry_time
                total_duration_minutes += duration.total_seconds() / 60
                total_count += 1
        
        for visit in completed_student_visits:
            if visit.entry_time and visit.exit_time:
                duration = visit.exit_time - visit.entry_time
                total_duration_minutes += duration.total_seconds() / 60
                total_count += 1
        
        avg_duration = total_duration_minutes / total_count if total_count > 0 else 0
        
        result = {
            'avg_duration_minutes': round(avg_duration, 1),
            'avg_duration_hours': round(avg_duration / 60, 1),
            'completed_visits_count': total_count
        }
        try:
            if AVG_VISIT_DURATION_MIN:
                AVG_VISIT_DURATION_MIN.set(result['avg_duration_minutes'])
        except Exception:
            pass
        return result
    
    def get_no_show_count(self):
        """Количество no-show: запланированные визиты, время в прошлом, без check-in."""
        now = timezone.now()
        count_official = Visit.objects.filter(expected_entry_time__lt=now, entry_time__isnull=True, status='AWAITING').count()
        try:
            if NO_SHOW_GAUGE:
                NO_SHOW_GAUGE.set(count_official)
        except Exception:
            pass
        return count_official
    
    def get_department_stats(self):
        """Статистика по департаментам с кэшированием"""
        cache_key = "dash:department_stats"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        # Оптимизированный запрос с агрегацией
        from django.db.models import Q, Case, When, IntegerField
        
        departments = Department.objects.annotate(
            visits_count=Count('visit', distinct=True),
            student_visits_count=Count('studentvisit', distinct=True),
            active_visits_count=Count(
                Case(
                    When(Q(visit__status='CHECKED_IN'), then=1),
                    output_field=IntegerField()
                ),
                distinct=True
            ) + Count(
                Case(
                    When(Q(studentvisit__status='CHECKED_IN'), then=1),
                    output_field=IntegerField()
                ),
                distinct=True
            )
        ).values('id', 'name', 'visits_count', 'student_visits_count', 'active_visits_count')
        
        stats = []
        for dept in departments:
            total_visits = dept['visits_count'] + dept['student_visits_count']
            stats.append({
                'department_id': dept['id'],
                'department': dept['name'],
                'total_visits': total_visits,
                'official_visits': dept['visits_count'],
                'student_visits': dept['student_visits_count'],
                'active_visits': dept['active_visits_count']
            })
        
        # Сортируем по общему количеству визитов
        stats.sort(key=lambda x: x['total_visits'], reverse=True)
        
        cache.set(cache_key, stats, timeout=300)  # 5 минут
        return stats
    
    def get_hourly_stats(self):
        """Почасовая статистика за последние 24 часа с кэшированием."""
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        cache_key = f"dash:hourly_stats:{now.hour}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        start = now - timedelta(hours=23)

        from django.db.models.functions import TruncHour

        visit_agg = (
            Visit.objects.filter(entry_time__gte=start, entry_time__lte=now + timedelta(hours=1))
            .annotate(h=TruncHour('entry_time'))
            .values('h')
            .annotate(cnt=Count('id'))
        )
        student_agg = (
            StudentVisit.objects.filter(entry_time__gte=start, entry_time__lte=now + timedelta(hours=1))
            .annotate(h=TruncHour('entry_time'))
            .values('h')
            .annotate(cnt=Count('id'))
        )

        # Приводим к словарям для быстрого объединения
        v_map = {row['h']: row['cnt'] for row in visit_agg}
        sv_map = {row['h']: row['cnt'] for row in student_agg}

        stats = []
        for i in range(24):
            hour = start + timedelta(hours=i)
            v = v_map.get(hour, 0)
            sv = sv_map.get(hour, 0)
            stats.append({
                'hour': hour.strftime('%H:00'),
                'timestamp': hour.isoformat(),
                'visits': v,
                'student_visits': sv,
                'total': v + sv,
            })
        
        cache.set(cache_key, stats, timeout=1800)  # 30 минут
        return stats
    
    def get_recent_events(self, limit=10):
        """Последние события"""
        cache_key = f"dash:events:limit={limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        events = RealtimeEvent.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')[:limit]
        
        data = [
            {
                'id': event.id,
                'type': event.event_type,
                'title': event.title,
                'message': event.message,
                'priority': event.priority,
                'timestamp': event.created_at.isoformat(),
                'is_read': event.is_read
            }
            for event in events
        ]
        cache.set(cache_key, data, timeout=5)
        return data
    
    def get_security_alerts(self):
        """Предупреждения безопасности"""
        alerts = RealtimeEvent.objects.filter(
            event_type='security_alert',
            is_read=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')
        
        return [
            {
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority,
                'timestamp': alert.created_at.isoformat()
            }
            for alert in alerts
        ]
    
    def calculate_duration_minutes(self, start_time):
        """Вычисление длительности в минутах"""
        if not start_time:
            return 0
        
        duration = timezone.now() - start_time
        return int(duration.total_seconds() / 60)
    
    def save_metrics_snapshot(self):
        """Сохранение снимка метрик в БД"""
        try:
            metrics = self.get_current_metrics()
            
            # Сохраняем основные метрики
            for metric_type in ['visitors_count', 'active_visits', 'today_registrations', 
                              'avg_visit_duration', 'department_stats', 'hourly_stats']:
                if metric_type in metrics:
                    DashboardMetric.objects.create(
                        metric_type=metric_type,
                        value=metrics[metric_type]
                    )
            
            # Очищаем старые метрики (старше 24 часов)
            old_threshold = timezone.now() - timedelta(hours=24)
            DashboardMetric.objects.filter(timestamp__lt=old_threshold).delete()
            
            logger.info("Dashboard metrics snapshot saved successfully")
            # Отправляем обновленные метрики подписчикам по WS
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "dashboard_updates",
                    {
                        "type": "dashboard_broadcast",
                        "message": {
                            "type": "metrics",
                            "data": metrics,
                        },
                    },
                )
            except Exception as ws_err:
                logger.warning("WS metrics broadcast failed: %s", ws_err)
            
        except Exception as e:
            logger.error("Error saving dashboard metrics: %s", e)


class RealtimeEventService:
    """
    Сервис для создания событий в реальном времени
    """
    
    @staticmethod
    def create_event(event_type, title, message, priority='normal', user=None, visit=None, data=None):
        """Создание нового события"""
        try:
            event = RealtimeEvent.objects.create(
                event_type=event_type,
                title=title,
                message=message,
                priority=priority,
                user=user,
                visit=visit,
                data=data or {}
            )
            
            logger.info("Realtime event created: %s", event.title)
            # Транслируем событие по WS
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "dashboard_updates",
                    {
                        "type": "dashboard_broadcast",
                        "message": {
                            "type": "event",
                            "data": {
                                "id": event.id,
                                "event_type": event.event_type,
                                "title": event.title,
                                "message": event.message,
                                "priority": event.priority,
                                "timestamp": event.created_at.isoformat(),
                            },
                        },
                    },
                )
            except Exception as ws_err:
                logger.warning("WS broadcast failed: %s", ws_err)
            return event
            
        except Exception as e:
            logger.error("Error creating realtime event: %s", e)
            return None
    
    @staticmethod
    def notify_visit_created(visit):
        """Уведомление о создании визита"""
        RealtimeEventService.create_event(
            event_type='visit_created',
            title='Новый визит зарегистрирован',
            message=f'Гость {visit.guest.full_name} зарегистрирован для посещения {visit.department.name}',
            priority='normal',
            visit=visit,
            data={
                'guest_name': visit.guest.full_name,
                'department': visit.department.name,
                'employee': visit.employee.get_full_name()
            }
        )
    
    @staticmethod
    def notify_visit_checked_in(visit):
        """Уведомление о входе посетителя"""
        RealtimeEventService.create_event(
            event_type='visit_checked_in',
            title='Посетитель вошел в здание',
            message=f'{visit.guest.full_name} вошел в здание',
            priority='normal',
            visit=visit,
            data={
                'guest_name': visit.guest.full_name,
                'entry_time': visit.entry_time.isoformat() if visit.entry_time else None
            }
        )
    
    @staticmethod
    def notify_visit_checked_out(visit):
        """Уведомление о выходе посетителя"""
        RealtimeEventService.create_event(
            event_type='visit_checked_out',
            title='Посетитель покинул здание',
            message=f'{visit.guest.full_name} покинул здание',
            priority='normal',
            visit=visit,
            data={
                'guest_name': visit.guest.full_name,
                'exit_time': visit.exit_time.isoformat() if visit.exit_time else None
            }
        )
    
    @staticmethod
    def notify_security_alert(title, message, data=None):
        """Предупреждение безопасности"""
        RealtimeEventService.create_event(
            event_type='security_alert',
            title=title,
            message=message,
            priority='high',
            data=data or {}
        )


# Синглтон сервиса
dashboard_service = DashboardMetricsService()
event_service = RealtimeEventService()
