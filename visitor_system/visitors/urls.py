from django.urls import path
from . import views
#from .views import create_group_invitation_view, group_invitation_fill_view, group_visit_card_view
from .views import qr_scan_view, qr_resolve_view, qr_code_view
from .dashboards import auto_checkin_dashboard, security_incidents_dashboard, hikcentral_dashboard
from .exports import (
    export_auto_checkin_pdf, export_auto_checkin_excel,
    export_security_incidents_pdf, export_security_incidents_excel,
    export_hikcentral_pdf, export_hikcentral_excel
)
from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework.throttling import AnonRateThrottle 

urlpatterns = [
    # --- единый URL для регистрации ---
    # path('register/', views.unified_register_visit_view, name='unified_register_visit'),
    # ------------------------------------
    
    path('register/', views.register_guest_view, name='register_guest'),
    # --- путь для регистрации студентов/абитуриентов ---
    path('register/student/', views.register_student_visit_view, name='register_student_visit'),
    path('register/group/<int:invitation_id>/', views.register_group_visit_view, name='register_group_visit'),
    
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
    path('exit/group/<int:visit_id>/', views.mark_group_exit_view, name='mark_group_exit'),
    
    path('special-feature/', views.example_special_feature_view, name='special_feature'),
    
    path('dashboard/employee/', views.employee_dashboard_view, name='employee_dashboard'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('ajax/employee-autocomplete/', views.employee_autocomplete_view, name='employee_autocomplete'),
    # --- путь для статистики --- (удалён)
    
    # --- путь для экспорта в Excel ---
    path('history/export/xlsx/', views.export_visits_xlsx, name='export_visits_xlsx'),
    # --- URL для получения деталей сотрудника ---
    path('ajax/employee-details/<int:user_id>/', views.get_employee_details_view, name='get_employee_details'),
    # --- URL для деталей департамента ---
    path('ajax/department-details/', views.get_department_details_view, name='get_department_details'),
    
    # --- API для HTMX polling ---
    path('api/counters/', views.get_counters_api, name='get_counters_api'),
    
    # --- Приглашения гостей ---
    path('invite/', views.create_guest_invitation, name='create_guest_invitation'),
    path('invite/fill/<uuid:token>/', views.guest_invitation_fill, name='guest_invitation_fill'),
    path('invite/finalize/<int:pk>/', views.finalize_guest_invitation, name='finalize_guest_invitation'),
    
    path('groups/create/', views.create_group_invitation_view, name='create_group_invitation'),
    path('groups/fill/<uuid:token>/', views.group_invitation_fill_view, name='group_invitation_fill'),
    path('groups/card/<int:pk>/', views.group_visit_card_view, name='group_visit_card'),
    path('groups/register/<int:invitation_id>/', views.register_group_visit_view, name='register_group_visit'),

    # --- QR ---
    path('qr/scan/', qr_scan_view, name='qr_scan'),
    path('qr/resolve/', qr_resolve_view, name='qr_resolve'),
    path('qr/code/<str:kind>/<int:pk>.png', qr_code_view, name='qr_code'),
    # DRF API для QR (анонимная с throttling)
    path('api/qr/resolve/', type('QRResolveAPI', (APIView,), {
        'throttle_classes': [AnonRateThrottle],
        'post': lambda self, request, *args, **kwargs: Response({'detail': 'use form endpoint'}, status=400)
    }).as_view(), name='qr_resolve_api'),
    
    # --- Dashboards ---
    path('dashboards/auto-checkin/', auto_checkin_dashboard, name='auto_checkin_dashboard'),
    path('dashboards/security-incidents/', security_incidents_dashboard, name='security_incidents_dashboard'),
    path('dashboards/hikcentral/', hikcentral_dashboard, name='hikcentral_dashboard'),
    
    # --- Dashboard Exports ---
    path('dashboards/auto-checkin/export/pdf/', export_auto_checkin_pdf, name='export_auto_checkin_pdf'),
    path('dashboards/auto-checkin/export/excel/', export_auto_checkin_excel, name='export_auto_checkin_excel'),
    path('dashboards/security-incidents/export/pdf/', export_security_incidents_pdf, name='export_security_incidents_pdf'),
    path('dashboards/security-incidents/export/excel/', export_security_incidents_excel, name='export_security_incidents_excel'),
    path('dashboards/hikcentral/export/pdf/', export_hikcentral_pdf, name='export_hikcentral_pdf'),
    path('dashboards/hikcentral/export/excel/', export_hikcentral_excel, name='export_hikcentral_excel'),
]

# DRF API маршруты регистрируются на уровне корневого urls.py (prefix /api/v1/)
