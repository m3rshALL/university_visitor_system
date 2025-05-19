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
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from visitors import views as visitor_views # Главная страница - панель сотрудника
from django.views.defaults import permission_denied, page_not_found, server_error
from django.shortcuts import render
from .pwa_views import service_worker_view


urlpatterns = [
    path('admin/', admin.site.urls),
    #path('auth/', include('authentication.urls')), # URL для аутентификации
    path('accounts/', include('allauth.urls')), # URL для аутентификации через allauth
    path('visitors/', include('visitors.urls')), # URL для гостей и визитов
    # Главная страница - перенаправляем на панель сотрудника
    path('', visitor_views.employee_dashboard_view, name='home'),
      path("select2/", include("django_select2.urls")),
    
    # Custom service worker view to handle encoding issues
    path('serviceworker.js', service_worker_view, name='serviceworker'),
    
    # PWA URLs, our custom service worker view override will take precedence
    path('', include('pwa.urls')),  # <- добавляем PWA
    
    # Страница для оффлайн-режима
    path('offline.html', 
         lambda request: render(request, 'offline.html'), 
         name='offline'),

    # Можно добавить другие корневые URL, если нужно
]

# Добавляем маршруты для статических и медиа файлов в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if not settings.DEBUG:
    handler403 = lambda request, exception: render(request, 'errors/403.html', status=403)
    handler404 = lambda request, exception: render(request, 'errors/404.html', status=404)
    handler500 = lambda request: render(request, 'errors/500.html', status=500)