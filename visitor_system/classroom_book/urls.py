# filepath: d:\university_visitor_system\visitor_system\classroom_book\urls.py
from django.urls import path
from . import views

app_name = 'classroom_book'

urlpatterns = [
    path('', views.classroom_index, name='classroom_index'),
    path('list/', views.classroom_list, name='classroom_list'),
    path('book/', views.book_classroom, name='book_classroom'),
    path('book/<int:classroom_id>/', views.book_classroom, name='book_specific_classroom'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('return/<uuid:booking_id>/', views.return_key, name='return_key'),
    path('cancel/<uuid:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('quick-booking/<str:token>/', views.quick_booking, name='quick_booking'),
    path('help/', views.help_page, name='help'),
    
    # API endpoints
    path('api/check-availability/', views.check_classroom_availability, name='check_availability'),
]