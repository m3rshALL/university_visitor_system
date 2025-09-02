"""
Middleware для аудита аутентификации и важных действий пользователей
"""
import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from visitors.models import AuditLog

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Middleware для расширенного аудита действий пользователей
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Сохраняем IP и User-Agent в request для использования в сигналах
        request._audit_ip = self.get_client_ip(request)
        request._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')[:1024]
        
        response = self.get_response(request)
        return response

    @staticmethod
    def get_client_ip(request):
        """Получает реальный IP клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@receiver(user_logged_in)
def audit_user_login(sender, request, user, **kwargs):
    """Аудит успешного входа в систему"""
    try:
        AuditLog.objects.create(
            action='login',
            model='User',
            object_id=str(user.pk),
            actor=user,
            ip_address=getattr(request, '_audit_ip', None),
            user_agent=getattr(request, '_audit_user_agent', ''),
            path=request.path,
            method=request.method,
            extra={
                'login_type': 'successful',
                'session_key': request.session.session_key,
            }
        )
        logger.info("User %s logged in from IP %s", user.username, 
                   getattr(request, '_audit_ip', 'unknown'))
    except Exception:
        logger.exception("Failed to write audit log for user login")


@receiver(user_logged_out)
def audit_user_logout(sender, request, user, **kwargs):
    """Аудит выхода из системы"""
    try:
        AuditLog.objects.create(
            action='logout',
            model='User',
            object_id=str(user.pk) if user else None,
            actor=user,
            ip_address=getattr(request, '_audit_ip', None),
            user_agent=getattr(request, '_audit_user_agent', ''),
            path=request.path,
            method=request.method,
            extra={
                'logout_type': 'normal',
                'session_key': request.session.session_key if hasattr(request, 'session') else None,
            }
        )
        logger.info("User %s logged out from IP %s", 
                   user.username if user else 'unknown',
                   getattr(request, '_audit_ip', 'unknown'))
    except Exception:
        logger.exception("Failed to write audit log for user logout")


@receiver(user_login_failed)
def audit_user_login_failed(sender, credentials, request, **kwargs):
    """Аудит неудачных попыток входа"""
    try:
        username = credentials.get('username', 'unknown')
        AuditLog.objects.create(
            action='login_failed',
            model='User',
            object_id=None,
            actor=None,
            ip_address=getattr(request, '_audit_ip', None),
            user_agent=getattr(request, '_audit_user_agent', ''),
            path=request.path,
            method=request.method,
            extra={
                'attempted_username': username,
                'failure_reason': 'invalid_credentials',
            }
        )
        logger.warning("Failed login attempt for username %s from IP %s", 
                      username, getattr(request, '_audit_ip', 'unknown'))
    except Exception:
        logger.exception("Failed to write audit log for failed login")


class AdminAuditMiddleware:
    """
    Middleware для аудита действий в админ-панели
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Аудит действий в админке
        if (request.path.startswith('/admin/') and 
            request.user.is_authenticated and 
            request.method in ['POST', 'PUT', 'DELETE']):
            self._audit_admin_action(request, response)
        
        return response

    def _audit_admin_action(self, request, response):
        """Аудит действий в админ-панели"""
        try:
            if response.status_code < 400:  # Успешное действие
                action_type = 'admin_action'
                if 'add' in request.path:
                    action_type = 'admin_create'
                elif 'change' in request.path:
                    action_type = 'admin_update'
                elif 'delete' in request.path:
                    action_type = 'admin_delete'
                
                AuditLog.objects.create(
                    action=action_type,
                    model='AdminAction',
                    object_id=None,
                    actor=request.user,
                    ip_address=AuditMiddleware.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:1024],
                    path=request.path,
                    method=request.method,
                    extra={
                        'admin_action': True,
                        'status_code': response.status_code,
                    }
                )
        except Exception:
            logger.exception("Failed to write admin audit log")
