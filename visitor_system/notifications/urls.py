from django.urls import path, include
from . import views

urlpatterns = [
    # WebPush URLs
    path('subscribe/', views.webpush_subscribe, name='webpush_subscribe'),
    path('unsubscribe/', views.webpush_unsubscribe, name='webpush_unsubscribe'),
    path('send-notification/', views.send_webpush_notification, name='send_webpush_notification'),
    path('get-public-key/', views.get_vapid_public_key, name='get_vapid_public_key'),
    
    # Django-webpush includes
    path('webpush/', include('webpush.urls')),
]
