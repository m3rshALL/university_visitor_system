"""
URL configuration for visitor_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# visitor_system/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter  # type: ignore
try:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView  # type: ignore
    _spectacular_available = True
except Exception:
    _spectacular_available = False
from django.conf import settings
from django.conf.urls.static import static
# from django.views.decorators.cache import cache_control
# from django.contrib.staticfiles.views import serve as serve_static
from visitors import views as visitor_views # Главная страница - панель сотрудника
# from django.views.defaults import permission_denied, page_not_found, server_error
from django.shortcuts import render
# from debug_toolbar.toolbar import debug_toolbar_urls
from visitors.views import manifest_json_view, service_worker_view
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db import connections
from django.core.cache import caches
from visitor_system.celery import app as celery_app


# Healthcheck views with safe fallbacks
def healthz_view(request):
    try:
        connections['default'].cursor().execute('SELECT 1')
        caches['default'].set('healthz', 'ok', 5)
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'degraded'})


def healthz_celery_view(request):
    try:
        workers = len(celery_app.control.ping(timeout=1.0) or [])
        return JsonResponse({'status': 'ok', 'workers': workers})
    except Exception:
        return JsonResponse({'status': 'degraded', 'workers': 0})

# Временный импорт для тестирования (удален после проверки)
# import sys
# sys.path.append('/app/visitor_system')
# from test_iin_view import test_iin_view

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('admin/', admin.site.urls),
    #path('auth/', include('authentication.urls')), # URL для аутентификации
    path('accounts/', include('allauth.urls')), # URL для аутентификации через allauth
    path('visitors/', include('visitors.urls')), # URL для гостей и визитов
    path('classroom-book/', include('classroom_book.urls', namespace='classroom_book')), # URL для бронирования аудиторий
    path('egov/', include('egov_integration.urls')), # URL для интеграции с egov.kz
    path('dashboard/', include('realtime_dashboard.urls')), # URL для дашборда в реальном времени
    # API schema & Swagger UI (если доступен drf-spectacular)
    *([
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/schema', SpectacularAPIView.as_view(), name='schema_noslash'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'),
             name='swagger-ui'),
        path('api/docs', SpectacularSwaggerView.as_view(url_name='schema'),
             name='swagger-ui_noslash'),
    ] if _spectacular_available else []),
    # Главная страница - перенаправляем на панель сотрудника
    path('', visitor_views.employee_dashboard_view, name='home'),
    path("select2/", include("django_select2.urls")),

    # Custom service worker view to handle encoding issues
    path('serviceworker.js', service_worker_view, name='serviceworker'),

    # Custom manifest.json view to handle syntax issues
    path('manifest.json', manifest_json_view, name='manifest'),

    # PWA URLs, our custom service worker view override will take precedence
    path('', include('pwa.urls')),  # <- добавляем PWA

    # Страница для оффлайн-режима
    path('offline.html', TemplateView.as_view(template_name='errors/offline.html'),
         name='offline'),

    # Healthcheck
    path('healthz', healthz_view, name='healthz'),
    path('healthz/celery', healthz_celery_view, name='healthz_celery'),
    # Временный маршрут для тестирования ИИН (удален после проверки)
    # path('test-iin/', test_iin_view, name='test_iin'),

    # Можно добавить другие корневые URL, если нужно
]

# DRF routers (API v1)
try:
    from visitors.api import VisitViewSet, StudentVisitViewSet
    _api_import_ok = True
except Exception:
    _api_import_ok = False

if _api_import_ok:
    drf_router = DefaultRouter()
    drf_router.register(r'visits', VisitViewSet, basename='api-visits')
    drf_router.register(r'student_visits', StudentVisitViewSet,
                        basename='api-student-visits')
    urlpatterns += [path('api/v1/', include((drf_router.urls, 'api'),
                                            namespace='api_v1'))]


# Добавляем маршруты для статических и медиа файлов в режиме DEBUG
if settings.DEBUG:
    # Keep media files as they were
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Для статики используем стандартную раздачу в DEBUG через django.contrib.staticfiles
    # urlpatterns.extend(debug_toolbar_urls())  # Добавляем URL-ы от debug_toolbar

if not settings.DEBUG:
    def handler403(request, exception):
        return render(request, 'errors/403.html', status=403)

    def handler404(request, exception):
        return render(request, 'errors/404.html', status=404)

    def handler500(request):
        return render(request, 'errors/500.html', status=500)