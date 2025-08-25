from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Notification


@login_required
def notification_list(request):
    """Страница со списком уведомлений пользователя"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'unread_count': notifications.filter(read=False).count()
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def mark_notification_read(request, pk):
    """Отметить уведомление как прочитанное"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    else:
        next_url = request.GET.get('next', 'notification_list')
        return redirect(next_url)


@login_required
def mark_all_read(request):
    """Отметить все уведомления как прочитанные"""
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    else:
        messages.success(request, 'Все уведомления отмечены как прочитанные')
        return redirect('notification_list')


@login_required
def notification_badge(request):
    """API для получения количества непрочитанных уведомлений"""
    count = Notification.objects.filter(
        recipient=request.user, 
        read=False
    ).count()
    
    return JsonResponse({'count': count})