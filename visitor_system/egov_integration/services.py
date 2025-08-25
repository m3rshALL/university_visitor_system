# egov_integration/services.py
import requests
import json
import logging
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
from .models import DocumentVerification, EgovAPILog, EgovSettings
import hashlib
import time


logger = logging.getLogger(__name__)


class EgovAPIException(Exception):
    """Исключение для ошибок API egov.kz"""
    pass


class EgovService:
    """
    Сервис для работы с API egov.kz
    """
    
    def __init__(self):
        # Инициализация настроек будет выполнена при первом обращении
        self._base_url = None
        self._api_key = None
        self._timeout = None
        self._max_retries = None
        self._settings_loaded = False
    
    def _load_settings(self):
        """Загрузка настроек при первом обращении"""
        if not self._settings_loaded:
            self._base_url = self._get_setting('EGOV_BASE_URL', 'https://data.egov.kz/api/v4')
            self._api_key = self._get_setting('EGOV_API_KEY', '', encrypted=True)
            self._timeout = int(self._get_setting('EGOV_TIMEOUT', '30'))
            self._max_retries = int(self._get_setting('EGOV_MAX_RETRIES', '3'))
            self._settings_loaded = True
    
    @property
    def base_url(self):
        self._load_settings()
        return self._base_url
    
    @property
    def api_key(self):
        self._load_settings()
        return self._api_key
    
    @property
    def timeout(self):
        self._load_settings()
        return self._timeout
    
    @property
    def max_retries(self):
        self._load_settings()
        return self._max_retries
        
    def _get_setting(self, name: str, default: str = '', encrypted: bool = False) -> str:
        """Получение настройки из базы данных или переменных окружения"""
        try:
            # Проверяем, что таблица существует
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='egov_integration_egovsettings')"
                )
                table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                raise EgovSettings.DoesNotExist("Таблица настроек не создана")
            
            setting = EgovSettings.objects.get(name=name)
            value = setting.value
            if encrypted and setting.is_encrypted:
                # Расшифровка значения
                f = Fernet(getattr(settings, 'IIN_ENCRYPTION_KEY', '').encode())
                value = f.decrypt(value.encode()).decode()
            return value
        except (EgovSettings.DoesNotExist, Exception):
            # Fallback на переменные окружения
            import os
            return os.getenv(name, default)
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        user=None,
        verification: Optional[DocumentVerification] = None
    ) -> Tuple[int, Dict]:
        """
        Выполнение запроса к API egov.kz с логированием
        """
        # Для egov.kz API ключ передается как параметр
        if '?' in endpoint:
            url = f"{self.base_url}{endpoint}&apiKey={self.api_key}"
        else:
            url = f"{self.base_url}{endpoint}?apiKey={self.api_key}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'UniversityVisitorSystem/1.0',
            'Accept': 'application/json'
        }
        
        start_time = time.time()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Логирование запроса
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                request_data=data,
                response_status=response.status_code,
                response_data=response.json() if response.content else None,
                response_time_ms=response_time_ms,
                user=user,
                verification=verification
            )
            
            if response.status_code >= 400:
                logger.error(
                    "API egov.kz error: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise EgovAPIException(f"API error: {response.status_code}")
            
            return response.status_code, response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error("Request to egov.kz failed: %s", e)
            # Логируем ошибку
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                request_data=data,
                response_status=0,
                response_data={'error': str(e)},
                response_time_ms=int((time.time() - start_time) * 1000),
                user=user,
                verification=verification
            )
            raise EgovAPIException(f"Request failed: {e}")
    
    def _log_api_call(
        self, 
        method: str, 
        endpoint: str, 
        request_data: Optional[Dict],
        response_status: int, 
        response_data: Optional[Dict],
        response_time_ms: int,
        user=None,
        verification: Optional[DocumentVerification] = None
    ):
        """Логирование вызова API"""
        try:
            EgovAPILog.objects.create(
                method=method,
                endpoint=endpoint,
                request_data=request_data,
                response_status=response_status,
                response_data=response_data,
                response_time_ms=response_time_ms,
                user=user,
                verification=verification
            )
        except Exception as e:
            logger.error("Failed to log API call: %s", e)
    
    def verify_iin(self, iin: str, user=None) -> DocumentVerification:
        """
        Проверка ИИН через API egov.kz
        """
        # Создаем запись о проверке
        verification = DocumentVerification.objects.create(
            document_type='iin',
            document_number=self._encrypt_document_number(iin),
            requested_by=user,
            status='pending'
        )
        
        try:
            # Подготавливаем данные для запроса
            request_data = {
                'iin': iin,
                'request_id': str(verification.id)
            }
            
            # Выполняем запрос к API
            status_code, response_data = self._make_request(
                method='GET',
                endpoint='/datasets/citizen_info',
                data=request_data,
                user=user,
                verification=verification
            )
            
            # Обрабатываем ответ
            if status_code == 200 and response_data.get('valid'):
                verification.status = 'verified'
                verification.verified_data = {
                    'full_name': response_data.get('full_name'),
                    'birth_date': response_data.get('birth_date'),
                    'gender': response_data.get('gender'),
                    'status': response_data.get('status')
                }
            else:
                verification.status = 'invalid'
                verification.error_message = response_data.get('message', 'Неизвестная ошибка')
            
            verification.egov_response = response_data
            verification.verified_at = timezone.now()
            verification.save()
            
            logger.info("IIN verification completed: %s - %s", iin, verification.status)
            return verification
            
        except Exception as e:
            verification.status = 'failed'
            verification.error_message = str(e)
            verification.save()
            logger.error("IIN verification failed: %s", e)
            return verification
    
    def verify_passport(self, passport_number: str, user=None) -> DocumentVerification:
        """
        Проверка паспорта через API egov.kz
        """
        verification = DocumentVerification.objects.create(
            document_type='passport',
            document_number=self._encrypt_document_number(passport_number),
            requested_by=user,
            status='pending'
        )
        
        try:
            request_data = {
                'passport_number': passport_number,
                'request_id': str(verification.id)
            }
            
            status_code, response_data = self._make_request(
                method='GET',
                endpoint='/datasets/passport_info',
                data=request_data,
                user=user,
                verification=verification
            )
            
            if status_code == 200 and response_data.get('valid'):
                verification.status = 'verified'
                verification.verified_data = {
                    'full_name': response_data.get('full_name'),
                    'issue_date': response_data.get('issue_date'),
                    'expiry_date': response_data.get('expiry_date'),
                    'issuer': response_data.get('issuer')
                }
            else:
                verification.status = 'invalid'
                verification.error_message = response_data.get('message', 'Неизвестная ошибка')
            
            verification.egov_response = response_data
            verification.verified_at = timezone.now()
            verification.save()
            
            return verification
            
        except Exception as e:
            verification.status = 'failed'
            verification.error_message = str(e)
            verification.save()
            logger.error(f"Passport verification failed: {e}")
            return verification
    
    def get_citizen_info(self, iin: str, user=None) -> Optional[Dict]:
        """
        Получение информации о гражданине по ИИН
        """
        try:
            request_data = {'iin': iin}
            
            status_code, response_data = self._make_request(
                method='GET',
                endpoint=f'/api/v1/citizen/{iin}',
                data=request_data,
                user=user
            )
            
            if status_code == 200:
                return response_data
            else:
                logger.warning(f"Failed to get citizen info for IIN: {iin}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting citizen info: {e}")
            return None
    
    def _encrypt_document_number(self, document_number: str) -> str:
        """Шифрование номера документа"""
        try:
            encryption_key = getattr(settings, 'IIN_ENCRYPTION_KEY', '')
            if not encryption_key:
                # Генерируем временный хеш если нет ключа шифрования
                return hashlib.sha256(document_number.encode()).hexdigest()
            
            # Проверяем формат ключа
            if len(encryption_key.encode()) != 44:  # Base64 32 байта = 44 символа
                logger.warning("IIN_ENCRYPTION_KEY has incorrect length, using hash fallback")
                return hashlib.sha256(document_number.encode()).hexdigest()
            
            f = Fernet(encryption_key.encode())
            return f.encrypt(document_number.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt document number: {e}")
            # Fallback - хешируем
            return hashlib.sha256(document_number.encode()).hexdigest()
    
    def check_api_health(self) -> Dict[str, Any]:
        """
        Проверка доступности API egov.kz
        """
        try:
            status_code, response_data = self._make_request(
                method='GET',
                endpoint='/health'
            )
            
            return {
                'status': 'healthy' if status_code == 200 else 'unhealthy',
                'response_time': response_data.get('response_time'),
                'version': response_data.get('version'),
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }


# Синглтон для использования в других частях приложения
egov_service = EgovService()
