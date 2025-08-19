# egov_integration/urls.py
from django.urls import path
from . import views

app_name = 'egov_integration'

urlpatterns = [
    # AJAX endpoints
    path('ajax/verify-iin/', views.verify_iin_ajax, name='verify_iin_ajax'),
    path('ajax/verify-passport/', views.verify_passport_ajax, name='verify_passport_ajax'),
    path('ajax/health/', views.api_health_check, name='api_health_check'),
    
    # Status endpoints
    path('verification/<uuid:verification_id>/', views.verification_status, name='verification_status'),
    path('verifications/', views.verification_list, name='verification_list'),
    
    # REST API endpoints
    path('api/verify/iin/', views.VerifyIINAPIView.as_view(), name='api_verify_iin'),
    path('api/verify/passport/', views.VerifyPassportAPIView.as_view(), name='api_verify_passport'),
]