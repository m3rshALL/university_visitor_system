"""
Dashboards для мониторинга и аналитики.

Включает:
- Dashboard автоматических check-in/out действий
- Dashboard HikCentral интеграции
- Dashboard security incidents
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.db.models import Count
from django.core.cache import cache
from datetime import timedelta
from collections import defaultdict
import logging

from .models import Visit, AuditLog, SecurityIncident

logger = logging.getLogger(__name__)

# Cache TTL settings (in seconds)
CACHE_TTL_SHORT = 120  # 2 minutes
CACHE_TTL_MEDIUM = 180  # 3 minutes
CACHE_TTL_LONG = 300  # 5 minutes


@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def auto_checkin_dashboard(request):
    """
    Dashboard для мониторинга автоматических check-in/checkout действий.
    
    Показывает:
    - Статистику автоматических действий за период
    - График проходов по часам
    - Последние автоматические действия из AuditLog
    - Аномалии (security incidents)
    """
    now = timezone.now()
    today = now.date()
    
    # Период для отображения (по умолчанию - сегодня)
    period = request.GET.get('period', 'today')
    
    # Попытка получить данные из кэша
    cache_key = f'dashboard:auto_checkin:{period}:{today.isoformat()}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.debug(f'Auto check-in dashboard cache HIT for period={period}')
        cached_data['from_cache'] = True
        return render(request, 'visitors/auto_checkin_dashboard.html', cached_data)
    
    logger.debug(f'Auto check-in dashboard cache MISS for period={period}')
    
    if period == 'today':
        start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        end_date = now
        period_label = 'Сегодня'
    elif period == 'week':
        start_date = now - timedelta(days=7)
        end_date = now
        period_label = 'Последние 7 дней'
    elif period == 'month':
        start_date = now - timedelta(days=30)
        end_date = now
        period_label = 'Последние 30 дней'
    else:
        start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        end_date = now
        period_label = 'Сегодня'
    
    # Статистика автоматических check-in
    auto_checkins = AuditLog.objects.filter(
        model='Visit',
        action=AuditLog.ACTION_UPDATE,
        user_agent='HikCentral FaceID System',
        created_at__gte=start_date,
        created_at__lte=end_date,
        changes__reason='Auto check-in via FaceID turnstile'
    )
    
    # Статистика автоматических checkouts
    auto_checkouts = AuditLog.objects.filter(
        model='Visit',
        action=AuditLog.ACTION_UPDATE,
        user_agent='HikCentral FaceID System',
        created_at__gte=start_date,
        created_at__lte=end_date,
        changes__reason='Auto checkout via FaceID turnstile'
    )
    
    checkin_count = auto_checkins.count()
    checkout_count = auto_checkouts.count()
    
    # График по часам (для сегодня или last 24h)
    if period == 'today':
        hourly_data = defaultdict(lambda: {'checkins': 0, 'checkouts': 0})
        
        for log in auto_checkins:
            hour = log.created_at.hour
            hourly_data[hour]['checkins'] += 1
        
        for log in auto_checkouts:
            hour = log.created_at.hour
            hourly_data[hour]['checkouts'] += 1
        
        # Формируем данные для графика
        hours = list(range(24))
        checkin_data = [hourly_data[h]['checkins'] for h in hours]
        checkout_data = [hourly_data[h]['checkouts'] for h in hours]
    else:
        # Для week/month - группируем по дням
        daily_data = defaultdict(lambda: {'checkins': 0, 'checkouts': 0})
        
        for log in auto_checkins:
            day = log.created_at.date()
            daily_data[day]['checkins'] += 1
        
        for log in auto_checkouts:
            day = log.created_at.date()
            daily_data[day]['checkouts'] += 1
        
        # Формируем данные для графика
        days = [(start_date.date() + timedelta(days=i)) for i in range((end_date.date() - start_date.date()).days + 1)]
        checkin_data = [daily_data[d]['checkins'] for d in days]
        checkout_data = [daily_data[d]['checkouts'] for d in days]
        hours = [d.strftime('%m-%d') for d in days]
    
    # Последние автоматические действия (топ-20)
    recent_actions = AuditLog.objects.filter(
        model='Visit',
        action=AuditLog.ACTION_UPDATE,
        user_agent='HikCentral FaceID System',
        created_at__gte=start_date,
        created_at__lte=end_date
    ).select_related('actor').order_by('-created_at')[:20]
    
    # Аномалии (security incidents)
    recent_incidents = SecurityIncident.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    ).select_related('visit__guest', 'visit__employee').order_by('-detected_at')[:10]
    
    incidents_count = SecurityIncident.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    ).count()
    
    # Текущие гости в здании
    guests_inside = Visit.objects.filter(
        status='CHECKED_IN',
        access_granted=True,
        access_revoked=False
    ).count()
    
    # Статистика по типам инцидентов
    incident_stats = SecurityIncident.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    ).values('incident_type').annotate(count=Count('id'))
    
    # Конвертируем QuerySet в list для JSON сериализации
    recent_actions_list = list(recent_actions)
    recent_incidents_list = list(recent_incidents)
    incident_stats_list = list(incident_stats)
    
    context = {
        'period': period,
        'period_label': period_label,
        'start_date': start_date,
        'end_date': end_date,
        'checkin_count': checkin_count,
        'checkout_count': checkout_count,
        'incidents_count': incidents_count,
        'guests_inside': guests_inside,
        'hourly_labels': hours,
        'checkin_data': checkin_data,
        'checkout_data': checkout_data,
        'recent_actions': recent_actions_list,  # Список вместо QuerySet
        'recent_incidents': recent_incidents_list,  # Список вместо QuerySet
        'incident_stats': incident_stats_list,  # Список вместо QuerySet
        'days': (end_date.date() - start_date.date()).days + 1,  # For export
        'from_cache': False,
    }
    
    # Сохраняем в кэш
    # Для 'today' - короткий TTL (2 мин), для week/month - средний (3 мин)
    ttl = CACHE_TTL_SHORT if period == 'today' else CACHE_TTL_MEDIUM
    cache.set(cache_key, context, ttl)
    logger.debug(f'Auto check-in dashboard cached with TTL={ttl}s')
    
    return render(request, 'visitors/auto_checkin_dashboard.html', context)


@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def security_incidents_dashboard(request):
    """
    Dashboard для мониторинга security incidents.
    
    Показывает:
    - Список активных инцидентов
    - Статистику по типам
    - Фильтрацию по severity, status, type
    """
    # Фильтры
    status_filter = request.GET.get('status', 'active')  # active, all, resolved
    severity_filter = request.GET.get('severity', '')
    type_filter = request.GET.get('type', '')
    
    # Попытка получить данные из кэша
    cache_key = f'dashboard:incidents:{status_filter}:{severity_filter}:{type_filter}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.debug(f'Security incidents dashboard cache HIT for filters={status_filter}/{severity_filter}/{type_filter}')
        cached_data['from_cache'] = True
        return render(request, 'visitors/security_incidents_dashboard.html', cached_data)
    
    logger.debug(f'Security incidents dashboard cache MISS')
    
    # Базовый queryset
    incidents = SecurityIncident.objects.select_related(
        'visit__guest', 'visit__employee', 'visit__department', 'assigned_to'
    )
    
    # Применяем фильтры
    if status_filter == 'active':
        incidents = incidents.filter(
            status__in=[SecurityIncident.STATUS_NEW, SecurityIncident.STATUS_INVESTIGATING]
        )
    elif status_filter == 'resolved':
        incidents = incidents.filter(status=SecurityIncident.STATUS_RESOLVED)
    elif status_filter == 'false_alarm':
        incidents = incidents.filter(status=SecurityIncident.STATUS_FALSE_ALARM)
    
    if severity_filter:
        incidents = incidents.filter(severity=severity_filter)
    
    if type_filter:
        incidents = incidents.filter(incident_type=type_filter)
    
    incidents = incidents.order_by('-detected_at')
    
    # Статистика
    total_incidents = SecurityIncident.objects.count()
    active_incidents = SecurityIncident.objects.filter(
        status__in=[SecurityIncident.STATUS_NEW, SecurityIncident.STATUS_INVESTIGATING]
    ).count()
    
    critical_incidents = SecurityIncident.objects.filter(
        severity=SecurityIncident.SEVERITY_CRITICAL,
        status__in=[SecurityIncident.STATUS_NEW, SecurityIncident.STATUS_INVESTIGATING]
    ).count()
    
    # Статистика по типам
    type_stats = SecurityIncident.objects.values('incident_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Статистика по severity
    severity_stats = SecurityIncident.objects.values('severity').annotate(
        count=Count('id')
    ).order_by('severity')
    
    # Конвертируем QuerySet в list для JSON сериализации
    incidents_list = list(incidents[:100])
    type_stats_list = list(type_stats)
    severity_stats_list = list(severity_stats)
    
    context = {
        'incidents': incidents_list,  # Список вместо QuerySet
        'total_incidents': total_incidents,
        'active_incidents': active_incidents,
        'critical_incidents': critical_incidents,
        'type_stats': type_stats_list,
        'severity_stats': severity_stats_list,
        'status_filter': status_filter,
        'severity_filter': severity_filter,
        'type_filter': type_filter,
        'incident_types': list(SecurityIncident.INCIDENT_TYPE_CHOICES),  # Tuple -> List
        'severity_levels': list(SecurityIncident.SEVERITY_CHOICES),  # Tuple -> List
        'days': 30,  # Default for exports
        'status': status_filter,
        'incident_type': type_filter,
        'severity': severity_filter,
        'from_cache': False,
    }
    
    # Сохраняем в кэш (короткий TTL т.к. incidents часто обновляются)
    cache.set(cache_key, context, CACHE_TTL_SHORT)
    logger.debug(f'Security incidents dashboard cached with TTL={CACHE_TTL_SHORT}s')
    
    return render(request, 'visitors/security_incidents_dashboard.html', context)


@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def hikcentral_dashboard(request):
    """
    Dashboard для мониторинга HikCentral интеграции.
    
    Показывает:
    - Статус подключения к HCP
    - Статистику визитов с HikCentral
    - Rate limiting status
    - Recent errors
    """
    from hikvision_integration.models import HikCentralServer
    
    # Попытка получить данные из кэша
    cache_key = 'dashboard:hikcentral:status'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.debug('HikCentral dashboard cache HIT')
        cached_data['from_cache'] = True
        return render(request, 'visitors/hikcentral_dashboard.html', cached_data)
    
    logger.debug('HikCentral dashboard cache MISS')
    
    # HikCentral servers
    hc_servers = HikCentralServer.objects.all()
    
    # Статистика визитов с HikCentral интеграцией
    total_with_hc = Visit.objects.filter(hikcentral_person_id__isnull=False).count()
    active_with_access = Visit.objects.filter(
        hikcentral_person_id__isnull=False,
        access_granted=True,
        access_revoked=False
    ).count()
    
    # Визиты с автоматическим check-in
    auto_checkedin = Visit.objects.filter(
        status='CHECKED_IN',
        first_entry_detected__isnull=False
    ).count()
    
    # Визиты с автоматическим checkout
    auto_checkedout = Visit.objects.filter(
        status='CHECKED_OUT',
        first_exit_detected__isnull=False
    ).count()
    
    # Средние показатели за последние 7 дней
    week_ago = timezone.now() - timedelta(days=7)
    
    avg_entry_time = Visit.objects.filter(
        first_entry_detected__gte=week_ago,
        entry_time__isnull=False
    ).count()
    
    # Последние ошибки в логах (из AuditLog или можно добавить специальную модель)
    # Пока оставим placeholder
    recent_errors = []
    
    # Rate limiter status (если есть доступ к метрикам)
    try:
        from hikvision_integration.rate_limiter import get_rate_limiter
        rate_limiter = get_rate_limiter()
        rate_limit_status = {
            'calls_limit': rate_limiter.calls,
            'window_seconds': rate_limiter.window,
            'current_calls': len(rate_limiter.timestamps),
            'available': rate_limiter.calls - len(rate_limiter.timestamps)
        }
    except Exception:
        rate_limit_status = None
    
    # Проверка доступности HCP серверов и конвертация в list
    servers_list = []
    for server in hc_servers:
        try:
            from hikvision_integration.services import HikCentralSession
            with HikCentralSession(server) as session:
                # Пробуем сделать простой запрос
                resp = session.get('/artemis/api/common/v1/status')
                is_available = (resp.status_code == 200)
        except Exception:
            is_available = False
        
        # Создаем dict вместо модели для JSON сериализации
        servers_list.append({
            'id': server.id,
            'name': server.name,
            'base_url': server.base_url,
            'integration_key': server.integration_key,
            'is_active': server.is_active,
            'is_available': is_available,
        })
    
    context = {
        'hc_servers': servers_list,  # Список словарей вместо QuerySet
        'total_with_hc': total_with_hc,
        'active_with_access': active_with_access,
        'auto_checkedin': auto_checkedin,
        'auto_checkedout': auto_checkedout,
        'avg_entry_time': avg_entry_time,
        'recent_errors': recent_errors,
        'rate_limit_status': rate_limit_status,
        'from_cache': False,
    }
    
    # Сохраняем в кэш (короткий TTL т.к. делаем внешний API запрос)
    # Кэшируем на 1 минуту чтобы не перегружать HCP API
    cache.set(cache_key, context, 60)  # 1 minute
    logger.debug('HikCentral dashboard cached with TTL=60s')
    
    return render(request, 'visitors/hikcentral_dashboard.html', context)

