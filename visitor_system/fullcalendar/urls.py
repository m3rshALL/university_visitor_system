from django.urls import path
from . import api_views

app_name = 'fullcalendar'

urlpatterns = [
    # API эндпоинт для получения событий календаря
    path('api/events/', api_views.calendar_events_api, name='calendar_events_api'),
    
    # Страница календаря
    path('', api_views.calendar_view, name='calendar_view'),
]
