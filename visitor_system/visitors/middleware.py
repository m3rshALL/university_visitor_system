import logging
from django.shortcuts import redirect
from django.urls import reverse, resolve # Добавили resolve
from django.urls.exceptions import Resolver404
from visitors.models import EmployeeProfile 
from django.apps import apps

logger = logging.getLogger(__name__)

SETUP_EXEMPT_URL_NAMES = [ 
    'profile_setup', 'account_logout', 'password_reset', 'password_reset_done', 
    'password_reset_confirm', 'password_reset_complete',
    # Дашборд и его API
    'realtime_dashboard:dashboard', 'realtime_dashboard:metrics_api', 'realtime_dashboard:events_api',
    'realtime_dashboard:widget_data_api', 'realtime_dashboard:mark_event_read'
]
SETUP_EXEMPT_URL_PREFIXES = ['/static/', '/media/', '/admin/', '/__debug__/', '/accounts/', '/dashboard/'] # Добавили дашборд

class ProfileSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            apps.get_model('visitors', 'EmployeeProfile')
            self.profile_model_available = True
        except LookupError:
            self.profile_model_available = False
            logger.warning("[Middleware] EmployeeProfile model not found on init. Profile check will be skipped.")

    def __call__(self, request):
        # --- Быстрые выходы до обработки view ---
        if not self.profile_model_available or \
           not request.user.is_authenticated or \
           request.user.is_anonymous or \
           request.user.is_superuser:
            return self.get_response(request)

        path = request.path_info
        for prefix in SETUP_EXEMPT_URL_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        try:
            resolver_match = resolve(path)
            if resolver_match.url_name in SETUP_EXEMPT_URL_NAMES:
                return self.get_response(request)
        except Resolver404:
            pass
        except Exception as e:
            logger.error("[Middleware] Error resolving URL name for path '%s': %s", path, e, exc_info=True)
            return self.get_response(request)

        # --- Проверка профиля до вызова view ---
        try:
            profile = request.user.employee_profile
            profile_complete = bool(profile.phone_number and profile.department)
            if not profile_complete:
                setup_url = reverse('profile_setup')
                if request.path != setup_url:
                    logger.info("[Middleware] User '%s' profile incomplete. Redirecting to setup.", request.user.username)
                    next_url = request.get_full_path()
                    if not next_url.startswith(setup_url):
                        redirect_url = f"{setup_url}?next={next_url}"
                        return redirect(redirect_url)
                    return redirect(setup_url)
        except EmployeeProfile.DoesNotExist:
            logger.error("[Middleware] EmployeeProfile DOES NOT EXIST for user '%s'. Redirecting to setup.", request.user.username)
            setup_url = reverse('profile_setup')
            if request.path != setup_url:
                return redirect(setup_url)
        except AttributeError:
            logger.error("[Middleware] User '%s' has no attribute 'employee_profile'.", request.user.username, exc_info=True)
        except Exception:
            logger.exception("[Middleware] Unexpected error accessing profile for user '%s'.", request.user.username)

        return self.get_response(request)

