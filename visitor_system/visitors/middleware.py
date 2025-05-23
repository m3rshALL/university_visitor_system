# visitors/middleware.py
import logging
from django.shortcuts import redirect
from django.urls import reverse, resolve # Добавили resolve
from django.urls.exceptions import Resolver404
from django.conf import settings # Для AUTH_USER_MODEL
from visitors.models import EmployeeProfile 
from django.apps import apps

logger = logging.getLogger(__name__)

SETUP_EXEMPT_URL_NAMES = [ 'profile_setup', 'account_logout', 'password_reset', 'password_reset_done', 'password_reset_confirm', 'password_reset_complete' ]
SETUP_EXEMPT_URL_PREFIXES = ['/static/', '/media/', '/admin/', '/__debug__/', '/accounts/'] # Добавили debug toolbar

class ProfileSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Проверим доступность модели при инициализации
        try:
             apps.get_model('visitors', 'EmployeeProfile') # Проверка загрузки модели
             self.profile_model_available = True
        except LookupError:
             self.profile_model_available = False
             logger.warning("[Middleware] EmployeeProfile model not found on init. Profile check will be skipped.")


    def __call__(self, request):
        # Сначала выполняем основную часть запроса
        # Это важно делать в начале, чтобы получить response от view
        response = self.get_response(request)

        # --- Быстрые выходы ---
        if not self.profile_model_available or \
           not request.user.is_authenticated or \
           request.user.is_anonymous or \
           request.user.is_superuser:
            return response

        path = request.path_info
        for prefix in SETUP_EXEMPT_URL_PREFIXES:
            if path.startswith(prefix):
                return response

        try:
            resolver_match = resolve(path)
            if resolver_match.url_name in SETUP_EXEMPT_URL_NAMES:
                return response
        except Resolver404:
            pass # Не имеет имени, проверяем профиль
        except Exception as e:
            logger.error(f"[Middleware] Error resolving URL name for path '{path}': {e}", exc_info=True)
            return response # Пропускаем при ошибке
        # --- Конец быстрых выходов ---


        # --- Основная проверка профиля через try...except ---
        try:
             # Пытаемся получить профиль напрямую
             profile = request.user.employee_profile
             # Если профиль получен, проверяем полноту
             profile_complete = bool(profile.phone_number and profile.department)

             if not profile_complete:
                  setup_url = reverse('profile_setup')
                  if request.path != setup_url:
                       logger.info(f"[Middleware] User '{request.user.username}' profile incomplete. Redirecting to setup.")
                       next_url = request.get_full_path()
                       if not next_url.startswith(setup_url):
                             redirect_url = f"{setup_url}?next={next_url}"
                             return redirect(redirect_url) # <-- Возвращаем HttpResponseRedirect
                       else:
                             return redirect(setup_url) # <-- Возвращаем HttpResponseRedirect
                  # else: Мы уже на странице настройки, ничего не делаем, вернется response

        except EmployeeProfile.DoesNotExist:
             # Сигнал не сработал ИЛИ пользователь как-то удалил профиль?
             logger.error(f"[Middleware] EmployeeProfile DOES NOT EXIST for user '{request.user.username}'. Redirecting to setup.")
             # Редиректим на настройку, там get_or_create должен сработать
             setup_url = reverse('profile_setup')
             if request.path != setup_url:
                 return redirect(setup_url) # <-- Возвращаем HttpResponseRedirect

        except AttributeError:
             # Этого не должно происходить, если user аутентифицирован,
             # но на всякий случай, если у user нет employee_profile
             logger.error(f"[Middleware] User '{request.user.username}' has no attribute 'employee_profile'.", exc_info=True)
             # Возможно, стоит пропустить проверку? Зависит от логики. Пока пропускаем.
             pass

        except Exception as e:
             # Логируем другие ошибки доступа к профилю
             logger.exception(f"[Middleware] Unexpected error accessing profile for user '{request.user.username}'.")
        # ----------------------------------------------------

        # Если не было редиректа или ошибки - возвращаем ОРИГИНАЛЬНЫЙ ответ от view
        return response

