# egov_integration/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
import json
import logging

from .services import egov_service, EgovAPIException
from .models import DocumentVerification
from visitors.models import Guest


logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def verify_iin_ajax(request):
    """
    AJAX endpoint для проверки ИИН
    """
    try:
        data = json.loads(request.body)
        iin = data.get('iin', '').strip()
        
        if not iin:
            return JsonResponse({
                'success': False,
                'error': 'ИИН не указан'
            }, status=400)
        
        if len(iin) != 12 or not iin.isdigit():
            return JsonResponse({
                'success': False,
                'error': 'ИИН должен содержать ровно 12 цифр'
            }, status=400)
        
        # Проверяем через egov.kz
        verification = egov_service.verify_iin(iin, user=request.user)
        
        response_data = {
            'success': verification.is_verified(),
            'verification_id': str(verification.id),
            'status': verification.status,
            'verified_at': verification.verified_at.isoformat() if verification.verified_at else None
        }
        
        if verification.is_verified() and verification.verified_data:
            response_data['data'] = {
                'full_name': verification.verified_data.get('full_name'),
                'birth_date': verification.verified_data.get('birth_date'),
                'gender': verification.verified_data.get('gender')
            }
        
        if verification.error_message:
            response_data['error'] = verification.error_message
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Неверный формат данных'
        }, status=400)
    
    except Exception as e:
        logger.error("Error in verify_iin_ajax: %s", e)
        return JsonResponse({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verify_passport_ajax(request):
    """
    AJAX endpoint для проверки паспорта
    """
    try:
        data = json.loads(request.body)
        passport_number = data.get('passport_number', '').strip()
        
        if not passport_number:
            return JsonResponse({
                'success': False,
                'error': 'Номер паспорта не указан'
            }, status=400)
        
        verification = egov_service.verify_passport(passport_number, user=request.user)
        
        response_data = {
            'success': verification.is_verified(),
            'verification_id': str(verification.id),
            'status': verification.status,
            'verified_at': verification.verified_at.isoformat() if verification.verified_at else None
        }
        
        if verification.is_verified() and verification.verified_data:
            response_data['data'] = verification.verified_data
        
        if verification.error_message:
            response_data['error'] = verification.error_message
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error("Error in verify_passport_ajax: %s", e)
        return JsonResponse({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }, status=500)


@login_required
def verification_status(request, verification_id):
    """
    Получение статуса проверки документа
    """
    verification = get_object_or_404(DocumentVerification, id=verification_id)
    
    response_data = {
        'id': str(verification.id),
        'status': verification.status,
        'document_type': verification.document_type,
        'created_at': verification.created_at.isoformat(),
        'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
        'is_verified': verification.is_verified()
    }
    
    if verification.verified_data:
        response_data['data'] = verification.verified_data
    
    if verification.error_message:
        response_data['error'] = verification.error_message
    
    return JsonResponse(response_data)


@login_required
@permission_required('egov_integration.view_documentverification', raise_exception=True)
def verification_list(request):
    """
    Список проверок документов
    """
    verifications = DocumentVerification.objects.filter(
        requested_by=request.user
    ).order_by('-created_at')[:50]  # Последние 50 проверок
    
    context = {
        'verifications': verifications,
        'title': 'Проверки документов'
    }
    
    return render(request, 'egov_integration/verification_list.html', context)


@login_required
def api_health_check(request):
    """
    Проверка состояния API egov.kz
    """
    health_status = egov_service.check_api_health()
    
    return JsonResponse({
        'egov_api': health_status,
        'timestamp': health_status['timestamp']
    })


# REST API Views
class VerifyIINAPIView(APIView):
    """
    REST API для проверки ИИН
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        iin = request.data.get('iin', '').strip()
        
        if not iin:
            return Response({
                'error': 'ИИН не указан'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(iin) != 12 or not iin.isdigit():
            return Response({
                'error': 'ИИН должен содержать ровно 12 цифр'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            verification = egov_service.verify_iin(iin, user=request.user)
            
            response_data = {
                'verification_id': str(verification.id),
                'status': verification.status,
                'is_verified': verification.is_verified(),
                'created_at': verification.created_at.isoformat(),
                'verified_at': verification.verified_at.isoformat() if verification.verified_at else None
            }
            
            if verification.is_verified() and verification.verified_data:
                response_data['data'] = verification.verified_data
            
            if verification.error_message:
                response_data['error'] = verification.error_message
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except EgovAPIException as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        except Exception as e:
            logger.error("Error in VerifyIINAPIView: %s", e)
            return Response({
                'error': 'Внутренняя ошибка сервера'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPassportAPIView(APIView):
    """
    REST API для проверки паспорта
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        passport_number = request.data.get('passport_number', '').strip()
        
        if not passport_number:
            return Response({
                'error': 'Номер паспорта не указан'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            verification = egov_service.verify_passport(passport_number, user=request.user)
            
            response_data = {
                'verification_id': str(verification.id),
                'status': verification.status,
                'is_verified': verification.is_verified(),
                'created_at': verification.created_at.isoformat(),
                'verified_at': verification.verified_at.isoformat() if verification.verified_at else None
            }
            
            if verification.is_verified() and verification.verified_data:
                response_data['data'] = verification.verified_data
            
            if verification.error_message:
                response_data['error'] = verification.error_message
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except EgovAPIException as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        except Exception as e:
            logger.error("Error in VerifyPassportAPIView: %s", e)
            return Response({
                'error': 'Внутренняя ошибка сервера'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)