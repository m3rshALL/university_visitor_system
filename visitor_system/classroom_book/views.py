from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Classroom, ClassroomKey, KeyBooking
from .forms import KeyBookingForm, QuickBookingConfirmForm
from .utils import generate_qr_code

import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
import pytz

@login_required
def classroom_index(request):
    """Главная страница модуля аудиторий"""
    tz = pytz.timezone('Asia/Almaty')
    now = datetime.now(tz)
    
    # Получаем активные бронирования пользователя
    active_bookings = KeyBooking.objects.filter(
        teacher=request.user,
        end_time__gte=now,
        is_cancelled=False,
        is_returned=False
    ).select_related('classroom', 'key').order_by('start_time')[:3]
    
    # Получаем ближайшие доступные аудитории
    classrooms = Classroom.objects.filter(is_active=True).order_by('building', 'number')[:6]
    
    # Получаем недавние бронирования пользователя
    recent_bookings = KeyBooking.objects.filter(
        teacher=request.user
    ).select_related('classroom').order_by('-created_at')[:5]
    
    context = {
        'active_bookings': active_bookings,
        'classrooms': classrooms,
        'recent_bookings': recent_bookings,
    }
    
    return render(request, 'classroom/index.html', context)

@login_required
def classroom_list(request):
    """Список всех доступных аудиторий"""
    # Получаем параметры фильтрации
    building = request.GET.get('building', '')
    floor = request.GET.get('floor', '')
    capacity = request.GET.get('capacity', '')
    features = request.GET.get('features', '')
    
    # Базовый запрос
    classrooms = Classroom.objects.filter(is_active=True)
    
    # Применяем фильтры
    if building:
        classrooms = classrooms.filter(building__icontains=building)
    if floor:
        classrooms = classrooms.filter(floor=floor)
    if capacity:
        classrooms = classrooms.filter(capacity__gte=capacity)
    if features:
        classrooms = classrooms.filter(features__icontains=features)
    
    # Сортировка
    classrooms = classrooms.order_by('building', 'floor', 'number')
    
    # Пагинация
    paginator = Paginator(classrooms, 12)  # 12 аудиторий на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Получаем уникальные значения для фильтров
    buildings = ['C1', 'C2', 'C3']  # Фиксированный список блоков университета
    floors = Classroom.objects.values_list('floor', flat=True).distinct().order_by('floor')
    
    context = {
        'page_obj': page_obj,
        'buildings': buildings,
        'floors': floors,
        'current_filters': {
            'building': building,
            'floor': floor,
            'capacity': capacity,
            'features': features,
        }
    }
    
    return render(request, 'classroom/classroom_list.html', context)

@login_required
def book_classroom(request, classroom_id=None):
    """Бронирование аудитории"""
    initial = {}
    if classroom_id:
        classroom = get_object_or_404(Classroom, id=classroom_id, is_active=True)
        initial['classroom'] = classroom
    
    if request.method == 'POST':
        form = KeyBookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.teacher = request.user
            
            # Выбираем доступный ключ
            classroom = form.cleaned_data['classroom']
            key = classroom.get_available_key()
            if key:
                booking.key = key
                key.is_available = False
                key.save()
            
            booking.save()
            
            # Генерируем QR-код
            booking_url = request.build_absolute_uri(
                reverse('classroom_book:quick_booking', kwargs={'token': booking.qr_code_token})
            )
            qr_code_base64 = generate_qr_code(booking_url)
            
            messages.success(request, 'Аудитория успешно забронирована!')
            
            return render(request, 'classroom/booking_success.html', {
                'booking': booking,
                'qr_code': qr_code_base64,
                'booking_url': booking_url
            })
    else:
        form = KeyBookingForm(initial=initial, user=request.user)
    
    # Исправлено: возвращаем правильный шаблон для формы бронирования
    return render(request, 'classroom/booking_form.html', {'form': form})

@login_required
def my_bookings(request):
    """Список бронирований текущего пользователя"""
    tz = pytz.timezone('Asia/Almaty')
    now = datetime.now(tz)
    
    # Активные бронирования (текущие и будущие)
    active = KeyBooking.objects.filter(
        teacher=request.user,
        end_time__gte=now,
        is_cancelled=False,
        is_returned=False
    ).select_related('classroom', 'key').order_by('start_time')
    
    # Прошедшие бронирования
    past = KeyBooking.objects.filter(
        teacher=request.user
    ).filter(
        Q(end_time__lt=now) | Q(is_returned=True) | Q(is_cancelled=True)
    ).select_related('classroom').order_by('-start_time')[:20]
    
    context = {
        'active': active,
        'past': past,
    }
    
    return render(request, 'classroom/my_bookings.html', context)

@login_required
def return_key(request, booking_id):
    """Отметка о возврате ключа"""
    booking = get_object_or_404(KeyBooking, id=booking_id, teacher=request.user)
    
    if request.method == 'POST':
        if booking.is_returned:
            messages.info(request, 'Ключ уже был возвращен')
        elif booking.is_cancelled:
            messages.warning(request, 'Бронирование было отменено')
        else:
            booking.is_returned = True
            booking.save()  # Метод save() в модели обновит статус и освободит ключ
            messages.success(request, 'Ключ успешно возвращен')
    
    return redirect('classroom_book:my_bookings')

@login_required
def cancel_booking(request, booking_id):
    """Отмена бронирования"""
    booking = get_object_or_404(KeyBooking, id=booking_id, teacher=request.user)
    
    if request.method == 'POST':
        if booking.is_returned:
            messages.info(request, 'Невозможно отменить бронирование - ключ уже возвращен')
        elif booking.is_cancelled:
            messages.info(request, 'Бронирование уже было отменено')
        else:
            booking.is_cancelled = True
            booking.save()  # Метод save() в модели обновит статус и освободит ключ
            messages.success(request, 'Бронирование успешно отменено')
    
    return redirect('classroom_book:my_bookings')

def quick_booking(request, token):
    """Страница быстрого бронирования по QR-коду"""
    booking = get_object_or_404(KeyBooking, qr_code_token=token)
    
    # Проверяем, не истекло ли бронирование
    if booking.is_cancelled or booking.is_returned:
        messages.warning(request, 'Это бронирование больше не активно')
        return redirect('classroom_book:classroom_index')
    
    if request.method == 'POST':
        form = QuickBookingConfirmForm(request.POST, instance=booking)
        if form.is_valid():
            if request.user.is_authenticated:
                # Проверяем, что пользователь имеет право на это бронирование
                if booking.teacher != request.user:
                    messages.warning(request, 'Это бронирование принадлежит другому пользователю')
                    return redirect('classroom_book:classroom_index')
                
                # Отмечаем ключ как выданный
                booking.status = 'issued'
                booking.save()
                
                messages.success(request, 'Бронирование успешно подтверждено!')
                return redirect('classroom_book:my_bookings')
            else:
                # Если пользователь не авторизован, перенаправляем на страницу входа
                return redirect(f"/accounts/login/?next={request.path}")
    else:
        form = QuickBookingConfirmForm()
    
    return render(request, 'classroom/quick_booking.html', {
        'booking': booking,
        'form': form
    })

@login_required
def check_classroom_availability(request):
    """API для проверки доступности аудитории"""
    classroom_id = request.GET.get('classroom_id')
    date_str = request.GET.get('date')
    
    if not classroom_id or not date_str:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        classroom = get_object_or_404(Classroom, id=classroom_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Сначала определяем tz
        almaty_tz = pytz.timezone('Asia/Almaty')
        # Получаем все бронирования для этой аудитории, которые пересекаются с выбранной датой
        # Используем make_aware для корректного tz-aware datetime
        naive_start = datetime.combine(date, datetime.min.time())
        naive_end = datetime.combine(date, datetime.max.time())
        start_of_day = timezone.make_aware(naive_start, almaty_tz)
        end_of_day = timezone.make_aware(naive_end, almaty_tz)
        start_of_day_utc = start_of_day.astimezone(pytz.UTC)
        end_of_day_utc = end_of_day.astimezone(pytz.UTC)
        bookings = KeyBooking.objects.filter(
            classroom=classroom,
            is_cancelled=False,
            is_returned=False,
            start_time__lt=end_of_day_utc,
            end_time__gt=start_of_day_utc
        ).order_by('start_time')
        
        # Конвертируем время в локальный часовой пояс
        busy_slots = []
        for booking in bookings:
            # Конвертируем UTC время в локальный часовой пояс
            start_local = booking.start_time.astimezone(almaty_tz)
            end_local = booking.end_time.astimezone(almaty_tz)
            
            busy_slots.append({
                'id': str(booking.id),  # UUID нужно преобразовать в строку
                'start': start_local.strftime('%H:%M'),
                'end': end_local.strftime('%H:%M'),
                'start_datetime': start_local.isoformat(),
                'end_datetime': end_local.isoformat(),
                'teacher': booking.teacher.get_full_name() or booking.teacher.username,
                'is_current_user': booking.teacher == request.user
            })
        
        return JsonResponse({
            'classroom_id': classroom_id,
            'date': date_str,
            'busy_slots': busy_slots
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def help_page(request):
    """Страница помощи и инструкций по использованию системы"""
    return render(request, 'classroom/help.html')