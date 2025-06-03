# visitors/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- единый URL для регистрации ---
    # path('register/', views.unified_register_visit_view, name='unified_register_visit'),
    # ------------------------------------
    
    path('register/', views.register_guest_view, name='register_guest'),
    # --- путь для регистрации студентов/абитуриентов ---
    path('register/student/', views.register_student_visit_view, name='register_student_visit'),
    #path('register-group/', views.register_group_visit_view, name='register_group_visit'),
    
    # --- URL для настройки профиля ---
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    
    # path('current/', views.current_guests_view, name='current_guests'),
    path('history/', views.visit_history_view, name='visit_history'),
    path('history/detail/<int:visit_id>/', views.visit_detail_view, name='visit_detail'),
    path('history/student/detail/<int:visit_id>/', views.student_visit_detail_view, name='student_visit_detail'),
    
    # --- пути для Check-in и Cancel ---
    path('checkin/<str:visit_kind>/<int:visit_id>/', views.check_in_visit, name='check_in_visit'),
    path('cancel/<str:visit_kind>/<int:visit_id>/', views.cancel_visit, name='cancel_visit'),
    # -----------------------------------------
    
    path('exit/<int:visit_id>/', views.mark_guest_exit_view, name='mark_guest_exit'),
    path('exit/student/<int:visit_id>/', views.mark_student_exit_view, name='mark_student_exit'),
    
    path('special-feature/', views.example_special_feature_view, name='special_feature'),
    
    path('dashboard/employee/', views.employee_dashboard_view, name='employee_dashboard'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('ajax/employee-autocomplete/', views.employee_autocomplete_view, name='employee_autocomplete'),
    # --- путь для статистики ---
    path('statistics/', views.visit_statistics_view, name='visit_statistics'),
    
    # --- путь для экспорта в Excel ---
    path('history/export/xlsx/', views.export_visits_xlsx, name='export_visits_xlsx'),
    
    path('ajax/employee-autocomplete/', views.employee_autocomplete_view, name='employee_autocomplete'),
    # --- URL для получения деталей сотрудника ---
    path('ajax/employee-details/<int:user_id>/', views.get_employee_details_view, name='get_employee_details'),
    # --- URL для деталей департамента ---
    path('ajax/department-details/', views.get_department_details_view, name='get_department_details'),
    
    # --- Приглашения гостей ---
    path('invite/', views.create_guest_invitation, name='create_guest_invitation'),
    path('invite/fill/<uuid:token>/', views.guest_invitation_fill, name='guest_invitation_fill'),
    path('invite/finalize/<int:pk>/', views.finalize_guest_invitation, name='finalize_guest_invitation'),
    
    
]
