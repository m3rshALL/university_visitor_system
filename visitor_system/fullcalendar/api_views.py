from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from datetime import datetime, timedelta

# Импортируем модели
from visitors.models import Visit, StudentVisit, VisitGroup
from classroom_book.models import KeyBooking


@login_required
@require_http_methods(["GET"])
def calendar_events_api(request):
    """
    API эндпоинт для получения всех событий календаря.
    Возвращает визиты и бронирования в формате FullCalendar.
    """
    
    # Получаем параметры фильтрации из запроса
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    events = []
    
    # Парсим даты, если переданы (FullCalendar передает ISO формат)
    start_date = None
    end_date = None
    
    if start:
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except ValueError:
            start_date = None
    
    if end:
        try:
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError:
            end_date = None
    
    # Если даты не переданы, берем период ±1 месяц от сегодня
    if not start_date or not end_date:
        today = timezone.now()
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=30)
    
    # Получаем обычные визиты
    visits_queryset = Visit.objects.select_related(
        'guest', 'employee', 'department'
    ).filter(
        Q(entry_time__range=[start_date, end_date]) |
        Q(expected_entry_time__range=[start_date, end_date])
    )
    
    for visit in visits_queryset:
        # Определяем время начала события
        event_start = visit.entry_time or visit.expected_entry_time
        if not event_start:
            continue
            
        # Определяем время окончания (если есть exit_time, иначе +2 часа)
        event_end = visit.exit_time
        if not event_end:
            event_end = event_start + timedelta(hours=2)
        
        # Определяем цвет на основе статуса
        color = get_visit_color(visit.status)
        
        # Создаем событие для календаря
        employee_name = (visit.employee.get_full_name() or
                        visit.employee.username)
        purpose_text = (visit.purpose[:100] + '...'
                       if len(visit.purpose) > 100 else visit.purpose)
        
        event = {
            'id': f'visit_{visit.id}',
            'title': f'Визит: {visit.guest.full_name}',
            'start': event_start.isoformat(),
            'end': event_end.isoformat(),
            'color': color,
            'textColor': '#ffffff',
            'extendedProps': {
                'type': 'visit',
                'status': visit.status,
                'guest_name': visit.guest.full_name,
                'employee_name': employee_name,
                'department': visit.department.name,
                'purpose': purpose_text,
                'url': f'/visitors/visit/{visit.id}/'
            }
        }
        events.append(event)
    
    # Получаем студенческие визиты
    student_visits_queryset = StudentVisit.objects.select_related(
        'guest', 'department', 'registered_by'
    ).filter(
        entry_time__range=[start_date, end_date]
    )
    
    for visit in student_visits_queryset:
        if not visit.entry_time:
            continue
            
        # Время окончания (если есть exit_time, иначе +4 часа для студентов)
        event_end = visit.exit_time
        if not event_end:
            event_end = visit.entry_time + timedelta(hours=4)
        
        color = get_visit_color(visit.status)
        purpose_text = (visit.purpose[:100] + '...'
                       if len(visit.purpose) > 100 else visit.purpose)
        
        event = {
            'id': f'student_visit_{visit.id}',
            'title': f'Студент: {visit.guest.full_name}',
            'start': visit.entry_time.isoformat(),
            'end': event_end.isoformat(),
            'color': color,
            'textColor': '#ffffff',
            'extendedProps': {
                'type': 'student_visit',
                'status': visit.status,
                'guest_name': visit.guest.full_name,
                'department': visit.department.name,
                'purpose': purpose_text,
                'student_id': getattr(visit, 'student_id', ''),
                'url': f'/visitors/student-visit/{visit.id}/'
            }
        }
        events.append(event)
    
    # Получаем групповые визиты
    group_visits_queryset = VisitGroup.objects.select_related(
        'department', 'employee'
    ).filter(
        expected_entry_time__range=[start_date, end_date]
    )
    
    for group in group_visits_queryset:
        if not group.expected_entry_time:
            continue
            
        # Групповые визиты обычно длятся 3 часа
        event_end = group.expected_entry_time + timedelta(hours=3)
        
        department_name = (group.department.name if group.department
                          else 'Не указан')
        employee_name = (group.employee.get_full_name()
                        if group.employee else 'Не указан')
        
        purpose_text = ''
        if group.purpose_other_text:
            if len(group.purpose_other_text) > 100:
                purpose_text = group.purpose_other_text[:100] + '...'
            else:
                purpose_text = group.purpose_other_text
        else:
            purpose_text = 'Не указано'
        
        event = {
            'id': f'group_visit_{group.id}',
            'title': f'Группа: {group.group_name}',
            'start': group.expected_entry_time.isoformat(),
            'end': event_end.isoformat(),
            'color': '#6c5ce7',  # Фиолетовый для групп
            'textColor': '#ffffff',
            'extendedProps': {
                'type': 'group_visit',
                'group_name': group.group_name,
                'department': department_name,
                'employee_name': employee_name,
                'purpose': purpose_text,
            }
        }
        events.append(event)
    
    # Получаем бронирования аудиторий
    bookings_queryset = KeyBooking.objects.select_related(
        'classroom', 'teacher', 'key'
    ).filter(
        start_time__range=[start_date, end_date],
        is_cancelled=False
    )
    
    for booking in bookings_queryset:
        color = get_booking_color(booking.status)
        teacher_name = (booking.teacher.get_full_name() or
                       booking.teacher.username)
        purpose_text = (booking.purpose[:100] + '...'
                       if len(booking.purpose) > 100 else booking.purpose)
        
        event = {
            'id': f'booking_{booking.id}',
            'title': f'Аудитория: {booking.classroom.number}',
            'start': booking.start_time.isoformat(),
            'end': booking.end_time.isoformat(),
            'color': color,
            'textColor': '#ffffff',
            'extendedProps': {
                'type': 'classroom_booking',
                'status': booking.status,
                'classroom': str(booking.classroom),
                'teacher_name': teacher_name,
                'purpose': purpose_text,
                'key_number': (booking.key.key_number if booking.key
                              else 'Не назначен'),
            }
        }
        events.append(event)
    
    return JsonResponse(events, safe=False)


def get_visit_color(status):
    """Возвращает цвет для визита на основе статуса"""
    colors = {
        'AWAITING': '#74b9ff',      # Голубой - ожидает
        'CHECKED_IN': '#00b894',    # Зеленый - в здании
        'CHECKED_OUT': '#636e72',   # Серый - вышел
        'CANCELLED': '#d63031',     # Красный - отменен
    }
    return colors.get(status, '#636e72')


def get_booking_color(status):
    """Возвращает цвет для бронирования на основе статуса"""
    colors = {
        'reserved': '#fdcb6e',      # Желтый - забронировано
        'issued': '#e17055',        # Оранжевый - выдан ключ
        'returned': '#00b894',      # Зеленый - возвращен
        'expired': '#d63031',       # Красный - просрочен
        'cancelled': '#636e72',     # Серый - отменен
    }
    return colors.get(status, '#636e72')


@login_required
@require_http_methods(["GET"])
def calendar_view(request):
    """
    Представление для отображения страницы календаря
    """
    context = {
        'page_title': 'Календарь событий',
    }
    
    return render(request, 'calendar/view.html', context)