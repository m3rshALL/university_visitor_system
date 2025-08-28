from django.urls import path
from . import views

app_name = 'realtime_dashboard'

urlpatterns = [
    # Основные страницы
    path('', views.dashboard_view, name='dashboard'),
    
    # AJAX API
    path('api/metrics/', views.dashboard_metrics_api, name='metrics_api'),
    path('api/metrics/test/', views.dashboard_metrics_test_api, name='metrics_test_api'),
    path('api/events/', views.dashboard_events_api, name='events_api'),
    path('api/events/<int:event_id>/read/', views.mark_event_read, name='mark_event_read'),
    path('api/widgets/<int:widget_id>/data/', views.widget_data_api, name='widget_data_api'),
    # Экспорт CSV активных визитов
    path('api/active_visits.csv', views.active_visits_csv, name='active_visits_csv'),
    path('api/active_visits/', views.active_visits_csv, name='active_visits_csv_alt'),
    path('api/active_visits', views.active_visits_csv, name='active_visits_csv_alt2'),
]

# Добавляем REST API только если доступен REST Framework
if hasattr(views, 'REST_FRAMEWORK_AVAILABLE') and views.REST_FRAMEWORK_AVAILABLE:
    urlpatterns += [
        path('api/v1/metrics/', views.DashboardMetricsAPIView.as_view(), name='api_metrics'),
        path('api/v1/events/', views.RealtimeEventsAPIView.as_view(), name='api_events'),
    ]
