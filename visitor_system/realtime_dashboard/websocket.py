from django.urls import path
from .ws_consumers import DashboardConsumer

websocket_urlpatterns = [
    path('ws/dashboard/', DashboardConsumer.as_asgi()),
]


