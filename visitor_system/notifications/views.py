from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import logging

from .models import Notification, WebPushSubscription, WebPushMessage
from .utils import send_webpush_notification as send_push

logger = logging.getLogger(__name__)


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


# WebPush Views

@login_required
def get_vapid_public_key(request):
    """Получение публичного VAPID ключа для фронтенда"""
    import base64
    from cryptography.hazmat.primitives import serialization
    
    try:
        # Получаем PEM ключ из настроек
        pem_key_b64 = settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY', '')
        
        if not pem_key_b64:
            return JsonResponse({'error': 'VAPID ключ не настроен'}, status=500)
        
        # Исправляем padding для base64
        missing_padding = len(pem_key_b64) % 4
        if missing_padding:
            pem_key_b64 += '=' * (4 - missing_padding)
        
        # Декодируем base64 PEM ключ
        pem_key = base64.b64decode(pem_key_b64).decode('utf-8')
        
        # Загружаем публичный ключ
        public_key = serialization.load_pem_public_key(pem_key.encode('utf-8'))
        
        # Получаем сырые байты в формате uncompressed point для WebPush
        raw_key = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Конвертируем в base64url (без padding) для WebPush API
        vapid_key = base64.urlsafe_b64encode(raw_key).decode('utf-8').rstrip('=')
        
        return JsonResponse({'public_key': vapid_key})
        
    except Exception as e:
        print(f"Ошибка конвертации VAPID ключа: {e}")
        return JsonResponse({'error': 'Ошибка обработки VAPID ключа'}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def webpush_subscribe(request):
    """Подписка на WebPush уведомления"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        p256dh = data.get('keys', {}).get('p256dh')
        auth = data.get('keys', {}).get('auth')
        
        if not all([endpoint, p256dh, auth]):
            return JsonResponse({'error': 'Недостаточно данных подписки'}, status=400)
        
        # Определяем устройство по User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_name = _get_device_name(user_agent)
        
        # Создаем или обновляем подписку
        subscription, created = WebPushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh_key': p256dh,
                'auth_key': auth,
                'user_agent': user_agent,
                'device_name': device_name,
                'is_active': True,
            }
        )
        
        logger.info(
            f'WebPush подписка {"создана" if created else "обновлена"} '
            f'для пользователя {request.user.username}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Подписка на уведомления успешно оформлена',
            'subscription_id': subscription.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f'Ошибка при создании WebPush подписки: {str(e)}')
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def webpush_unsubscribe(request):
    """Отписка от WebPush уведомлений"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return JsonResponse({'error': 'Endpoint не указан'}, status=400)
        
        # Деактивируем подписку
        updated = WebPushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint
        ).update(is_active=False)
        
        if updated:
            logger.info(
                f'WebPush подписка деактивирована для пользователя '
                f'{request.user.username}'
            )
            return JsonResponse({
                'success': True,
                'message': 'Подписка на уведомления отменена'
            })
        else:
            return JsonResponse({'error': 'Подписка не найдена'}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f'Ошибка при отписке от WebPush: {str(e)}')
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)


@login_required
@require_http_methods(["POST"])
def send_webpush_notification(request):
    """Отправка WebPush уведомления (для админов/тестирования)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Тестовое уведомление')
        body = data.get('body', 'Это тестовое уведомление')
        target_user_id = data.get('user_id')
        
        if target_user_id:
            # Отправляем конкретному пользователю
            from django.contrib.auth.models import User
            try:
                target_user = User.objects.get(id=target_user_id)
                result = send_push(target_user, title, body)
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден'}, status=404)
        else:
            # Отправляем всем (тестовый режим)
            result = send_push(request.user, title, body)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Уведомление отправлено {result["sent_count"]} подписчикам'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Ошибки при отправке: {result["errors"]}'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f'Ошибка при отправке WebPush уведомления: {str(e)}')
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)


def _get_device_name(user_agent):
    """Определение названия устройства по User-Agent"""
    user_agent = user_agent.lower()
    
    if 'mobile' in user_agent or 'android' in user_agent:
        if 'android' in user_agent:
            return 'Android устройство'
        elif 'iphone' in user_agent:
            return 'iPhone'
        elif 'ipad' in user_agent:
            return 'iPad'
        else:
            return 'Мобильное устройство'
    elif 'windows' in user_agent:
        return 'Windows компьютер'
    elif 'macintosh' in user_agent or 'mac os' in user_agent:
        return 'Mac компьютер'
    elif 'linux' in user_agent:
        return 'Linux компьютер'
    else:
        return 'Неизвестное устройство'
