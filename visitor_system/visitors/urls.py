# visitors/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- Новый единый URL для регистрации ---
    # path('register/', views.unified_register_visit_view, name='unified_register_visit'),
    # ------------------------------------
    
    path('register/', views.register_guest_view, name='register_guest'),
    # --- Новый путь для регистрации студентов/абитуриентов ---
    path('register/student/', views.register_student_visit_view, name='register_student_visit'),
    # --- Новый URL для настройки профиля ---
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    
    path('current/', views.current_guests_view, name='current_guests'),
    path('history/', views.visit_history_view, name='visit_history'),
    path('history/detail/<int:visit_id>/', views.visit_detail_view, name='visit_detail'),
    path('history/student/detail/<int:visit_id>/', views.student_visit_detail_view, name='student_visit_detail'),
    
    # --- Новые пути для Check-in и Cancel ---
    # Мы передаем 'visit_kind' как параметр в view
    path('checkin/<str:visit_kind>/<int:visit_id>/', views.check_in_visit, name='check_in_visit'),
    path('cancel/<str:visit_kind>/<int:visit_id>/', views.cancel_visit, name='cancel_visit'),
    # -----------------------------------------
    
    path('exit/<int:visit_id>/', views.mark_guest_exit_view, name='mark_guest_exit'),
    path('exit/student/<int:visit_id>/', views.mark_student_exit_view, name='mark_student_exit'),
    
    path('dashboard/employee/', views.employee_dashboard_view, name='employee_dashboard'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('ajax/employee-autocomplete/', views.employee_autocomplete_view, name='employee_autocomplete'),
    # --- Новый путь для статистики ---
    path('statistics/', views.visit_statistics_view, name='visit_statistics'),
    
    # --- Новый путь для экспорта в Excel ---
    path('history/export/xlsx/', views.export_visits_xlsx, name='export_visits_xlsx'),
    
    path('ajax/employee-autocomplete/', views.employee_autocomplete_view, name='employee_autocomplete'),
    # --- Новый URL для получения деталей сотрудника ---
    path('ajax/employee-details/<int:user_id>/', views.get_employee_details_view, name='get_employee_details'),
    # --- Новый URL для деталей департамента ---
    path('ajax/department-details/', views.get_department_details_view, name='get_department_details'),
    
]
