from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from itertools import chain
from operator import attrgetter
from .visitors.models import Visit, StudentVisit, EmployeeProfile,\
                            GuestInvitation, STATUS_AWAITING_ARRIVAL, GroupInvitation
from django.shortcuts import render
from django.contrib.auth.models import User

@login_required
def employee_dashboard_view(request):
    """Панель управления для обычного сотрудника."""
    user = request.user
    today = timezone.now().date()
    one_week_later = today + timedelta(days=7)
    # Получаем департамент текущего сотрудника
    try:
        user_department = user.employee_profile.department
    except (AttributeError, EmployeeProfile.DoesNotExist):
        user_department = None
    # Получаем визиты на ближайшую неделю для сотрудников своего департамента
    if user_department:
        # Получаем всех сотрудников департамента
        department_employee_ids = User.objects.filter(
            employee_profile__department=user_department
        ).values_list('id', flat=True)
        # Получаем визиты всех сотрудников департамента
        upcoming_visits_qs = Visit.objects.filter(
            employee_id__in=department_employee_ids,  # Фильтруем по списку ID сотрудников департамента
            expected_entry_time__date__gte=today,
            expected_entry_time__date__lt=one_week_later,
            status=STATUS_AWAITING_ARRIVAL,  # Ожидаемая регистрация
        ).select_related('guest', 'department', 'employee').order_by('expected_entry_time')
    else:
        # Если у пользователя нет департамента, показываем только его визиты
        upcoming_visits_qs = Visit.objects.filter(
            employee=user,
            expected_entry_time__date__gte=today,
            expected_entry_time__date__lt=one_week_later,
            status=STATUS_AWAITING_ARRIVAL,  # Ожидаемая регистрация
        ).select_related('guest', 'department', 'employee').order_by('expected_entry_time')
    # Convert queryset to list and add visit_kind for template URL generation
    upcoming_visits_week_list = list(upcoming_visits_qs)
    for visit_obj in upcoming_visits_week_list:
        visit_obj.visit_kind = 'official'
    # Гости, которых ожидает данный сотрудник и которые еще не вышли
    my_current_guests = Visit.objects.filter(
        employee=user,
        exit_time__isnull=True
    ).select_related('guest', 'department')
    # История визитов, связанных с этим сотрудником (как принимающий или регистрирующий)
    my_visit_history = Visit.objects.filter(
        Q(employee=user) | Q(registered_by=user)
    ).select_related('guest', 'department', 'employee', 'registered_by').order_by('-entry_time')[:20] # Последние 20
    # Данные для графика активности визитов
    # Генерируем данные для разных периодов (сегодня, неделя, месяц)
    visit_chart_data = {}
    # Фильтр по текущему департаменту пользователя
    department_filter = Q(department=user_department) if user_department else Q(employee=user)
    # Данные для графика по часам (сегодня)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    hourly_data = [0] * 24  # Инициализируем нулями для каждого часа
    # Получаем данные для официальных визитов по часам
    today_visits = Visit.objects.filter(
        department_filter, 
        entry_time__gte=today_start,
        entry_time__lt=today_end
    ).values('entry_time__hour').annotate(count=Count('id'))
    # Суммируем данные
    for visit in today_visits:
        hour = visit['entry_time__hour']
        if 0 <= hour < 24:  # Проверка на всякий случай
            hourly_data[hour] += visit['count']
    visit_chart_data['today'] = hourly_data
    # Данные для графика по дням недели
    week_start = today_start - timedelta(days=today_start.weekday())  # Понедельник текущей недели
    week_end = week_start + timedelta(days=7)
    weekly_data = [0] * 7  # Пн, Вт, Ср, Чт, Пт, Сб, Вс
    week_visits = Visit.objects.filter(
        department_filter,
        entry_time__gte=week_start,
        entry_time__lt=week_end
    ).values('entry_time__week_day').annotate(count=Count('id'))
    # В Django week_day: 1=воскресенье, 2=понедельник, ..., 7=суббота
    # Преобразуем в нашу индексацию: 0=понедельник, ..., 6=воскресенье
    for visit in week_visits:
        day = visit['entry_time__week_day']
        # Переводим из Django недельного дня в индекс массива (0-6, Пн-Вс)
        idx = (day - 2) % 7
        weekly_data[idx] += visit['count']
    visit_chart_data['week'] = weekly_data
    # Данные для графика по дням месяца
    month_start = today_start.replace(day=1)  # Первый день текущего месяца
    next_month = month_start.month + 1 if month_start.month < 12 else 1
    next_month_year = month_start.year if month_start.month < 12 else month_start.year + 1
    month_end = month_start.replace(year=next_month_year, month=next_month, day=1)
    # Инициализируем массив с нулями для каждого дня месяца (максимум 31 день)
    monthly_data = [0] * 31
    month_visits = Visit.objects.filter(
        department_filter,
        entry_time__gte=month_start,
        entry_time__lt=month_end
    ).values('entry_time__day').annotate(count=Count('id'))
    for visit in month_visits:
        day = visit['entry_time__day']
        if 1 <= day <= 31:  # Проверка на всякий случай
            monthly_data[day-1] += visit['count']  # -1 т.к. индексы начинаются с 0
    visit_chart_data['month'] = monthly_data    # Конвертируем в JSON для передачи в шаблон
    import json
    visit_chart_data_json = json.dumps(visit_chart_data)
    # Получаем недавние визиты (включая уже покинувших посетителей) 
    # за последние 7 дней из текущего департамента
    recent_time_threshold = timezone.now() - timedelta(days=7)
    if user_department:
        # Если есть департамент, фильтруем по нему
        recent_official_visits = Visit.objects.filter(
            department=user_department,
            entry_time__gte=recent_time_threshold
        ).select_related('guest', 'department', 'employee').order_by('-entry_time')[:10]
        recent_student_visits = StudentVisit.objects.filter(
            department=user_department,
            entry_time__gte=recent_time_threshold
        ).select_related('guest', 'department').order_by('-entry_time')[:10]
    else:
        # Если нет департамента, показываем визиты, связанные с пользователем
        recent_official_visits = Visit.objects.filter(
            Q(employee=user) | Q(registered_by=user),
            entry_time__gte=recent_time_threshold
        ).select_related('guest', 'department', 'employee').order_by('-entry_time')[:10]
        recent_student_visits = StudentVisit.objects.filter(
            registered_by=user,
            entry_time__gte=recent_time_threshold
        ).select_related('guest', 'department').order_by('-entry_time')[:10]
    # Добавляем атрибут для различения типов визитов в шаблоне
    for v in recent_official_visits: v.visit_kind = 'official'
    for v in recent_student_visits: v.visit_kind = 'student'
    # Объединяем и сортируем по времени входа (самые новые вверху)
    recent_visits = sorted(
        chain(recent_official_visits, recent_student_visits),
        key=attrgetter('entry_time'),        reverse=True
    )[:10]  # Берем только 10 самых недавних визитов
    # Получаем заполненные приглашения, ожидающие финализации
    pending_invitations = GuestInvitation.objects.filter(
        employee=user,
        is_filled=True,
        is_registered=False
    ).order_by('-created_at')
    # Отладочная информация
    print(f"DEBUG: User: {user.username}")
    print(f"DEBUG: Total pending invitations for user: {pending_invitations.count()}")
    for inv in pending_invitations:
        print(f"DEBUG: - {inv.guest_full_name} | created: {inv.created_at}")
    # Получаем групповые приглашения
    group_invitations = GroupInvitation.objects.filter(
        employee=user,
        is_filled=True,
        is_registered=False
    ).select_related('department').order_by('-created_at')
    context = {
        'upcoming_visits': upcoming_visits_week_list, # Визиты на неделю всего департамента
        'my_current_guests': my_current_guests,
        'my_visit_history': my_visit_history,
        'recent_visits': recent_visits,  # Добавляем недавние визиты в контекст
        'pending_invitations': pending_invitations,  # Добавляем заполненные приглашения
        'today': today,  # Добавляем переменную today для условного форматирования в шаблоне
        'department_name': user_department.name if user_department else "Нет департамента",
        'visit_chart_data': visit_chart_data_json,  # Добавляем данные для графика
        'group_invitations': group_invitations,
    }
    return render(request, 'visitors/employee_dashboard.html', context)
