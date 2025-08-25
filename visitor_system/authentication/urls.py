# authentication/urls.py
from django.urls import path
from . import views

# Для django-allauth:
# from allauth.account.views import LoginView, LogoutView
# path('login/', LoginView.as_view(), name='account_login'),
# path('logout/', LogoutView.as_view(), name='account_logout'),
# path('', include('allauth.urls')), # Включить все URL allauth, включая callback'и


# Заглушки:
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # URL для callback от Microsoft (нужно настроить в Azure AD)
    path('microsoft/callback/', views.microsoft_callback, name='microsoft_callback'),
]
