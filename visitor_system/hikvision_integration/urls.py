from django.urls import path
from . import views

app_name = 'hikvision_integration'

urlpatterns = [
    path('webhook/', views.webhook_view, name='webhook'),
]


