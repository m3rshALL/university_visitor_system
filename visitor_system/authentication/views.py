# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
# from django.contrib.auth.decorators import login_required

# Для реальной интеграции с MS Auth используйте django-allauth или MSAL Python
# Эти представления - просто заглушки

def login_view(request):
    """
    Эта страница должна инициировать процесс входа через Microsoft.
    Если используется django-allauth, здесь может быть ссылка типа:
    <a href="{% provider_login_url 'microsoft' %}">Войти через Microsoft</a>
    """
    # TODO: Интегрировать с MS Auth (например, редирект на URL провайдера)
    return render(request, 'registration/login.html')


def logout_view(request):
    """Выход пользователя из системы."""
    auth_logout(request)
    # Редирект на страницу входа или главную страницу
    # LOGOUT_REDIRECT_URL из settings.py будет использован, если не указать явно
    return redirect('login')


def microsoft_callback(request):
    """
    URL, на который Microsoft перенаправит пользователя после аутентификации.
    Здесь происходит обработка токена и вход пользователя в Django.
    Эту логику обычно берет на себя библиотека типа django-allauth.
    """
    # TODO: Обработать ответ от Microsoft, аутентифицировать пользователя в Django
    # Если успешно, редирект на LOGIN_REDIRECT_URL
    return redirect('employee_dashboard')  # Пример редиректа
