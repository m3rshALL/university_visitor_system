import base64
import logging
from typing import Any, Dict, List, Optional
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import HikDevice, HikCentralServer
import urllib3

# Отключаем предупреждения SSL для самоподписанных сертификатов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


class HikCentralSession:
    """Сессия для работы с HikCentral Professional OpenAPI (AK/SK подпись Artemis)."""

    def __init__(self, server: HikCentralServer):
        self.server = server
        self.base_url = server.base_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False  # Самоподписанные сертификаты
        logger.info(f"HikCentralSession initialized for {server.name}")

    @staticmethod
    def _calc_content_md5(body_bytes: bytes | None) -> str:
        import hashlib, base64 as b64
        if not body_bytes:
            return ''
        md5 = hashlib.md5(body_bytes).digest()
        return b64.b64encode(md5).decode('utf-8')

    @staticmethod
    def _canonical_headers(headers_for_sign: Dict[str, str]) -> tuple[str, str]:
        # Имёна заголовков строчными, сортировка по имени, формат "name:value\n"
        items = []
        for k, v in headers_for_sign.items():
            items.append((k.lower().strip(), ('' if v is None else str(v)).strip()))
        items.sort(key=lambda x: x[0])
        signed_names = ','.join([k for k, _ in items])
        lines = ''.join([f"{k}:{v}\n" for k, v in items])
        return signed_names, lines

    def _build_string_to_sign(
        self,
        method: str,
        accept: str | None,
        content_md5: str | None,
        content_type: str | None,
        date_hdr: str | None,
        headers_block: str,
        uri_with_query: str,
    ) -> str:
        # Согласно спецификации: METHOD\nAccept\nContent-MD5\nContent-Type\nDate\nHeadersUri
        # Если какого-либо из Accept/Content-MD5/Content-Type/Date нет в заголовках, строка для него НЕ добавляется.
        parts: list[str] = [method.upper()]
        if accept:
            parts.append(accept)
        if content_md5:
            parts.append(content_md5)
        if content_type:
            parts.append(content_type)
        if date_hdr:
            parts.append(date_hdr)
        string_to_sign = '\n'.join(parts) + '\n'
        string_to_sign += headers_block
        string_to_sign += uri_with_query
        return string_to_sign

    def _sign(self, string_to_sign: str) -> str:
        import hmac, hashlib, base64 as b64
        secret = (self.server.integration_secret or '').encode('utf-8')
        msg = string_to_sign.encode('utf-8')
        digest = hmac.new(secret, msg, hashlib.sha256).digest()
        return b64.b64encode(digest).decode('utf-8')

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> requests.Response:
        """Выполняет запрос к HikCentral OpenAPI с подписью AK/SK."""
        # Собираем URL и URI+query
        from urllib.parse import urlencode
        url = f"{self.base_url}{endpoint}"
        query_str = urlencode(params or {}, doseq=True)
        uri_with_query = endpoint + (f"?{query_str}" if query_str else '')

        # Тело и заголовки для подписи
        body_bytes = None
        # Всегда задаём Accept явно, иначе клиент может подставить */*
        accept = '*/*'
        # Для GET без тела Content-Type и Content-MD5 не используются
        content_type: str | None = None
        content_md5: str | None = None
        if data is not None:
            import json as _json
            body_bytes = _json.dumps(data, separators=(',', ':')).encode('utf-8')
            content_md5 = self._calc_content_md5(body_bytes)
            content_type = 'application/json;charset=UTF-8'

        import time, uuid, email.utils
        # Управляем включением Date через настройки
        date_hdr = email.utils.formatdate(usegmt=True) if getattr(settings, 'HIKCENTRAL_INCLUDE_DATE', False) else None
        x_ca_timestamp = str(int(time.time() * 1000))
        x_ca_nonce = str(uuid.uuid4())

        # Заголовки, участвующие в подписи
        headers_for_sign = {
            'x-ca-key': self.server.integration_key,
            'x-ca-timestamp': x_ca_timestamp,
            'x-ca-nonce': x_ca_nonce,
        }
        signed_names, headers_block = self._canonical_headers(headers_for_sign)

        # Итоговая строка для подписи
        string_to_sign = self._build_string_to_sign(
            method=method,
            accept=accept,
            content_md5=content_md5,
            content_type=content_type,
            date_hdr=date_hdr,
            headers_block=headers_block,
            uri_with_query=uri_with_query,
        )
        signature = self._sign(string_to_sign)

        # Финальные заголовки запроса
        headers = {
            'Accept': accept,
            'X-Ca-Key': self.server.integration_key,
            'X-Ca-Timestamp': x_ca_timestamp,
            'X-Ca-Nonce': x_ca_nonce,
            'X-Ca-Signature-Headers': signed_names,
            'X-Ca-Signature': signature,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if content_type:
            headers['Content-Type'] = content_type
        if date_hdr:
            headers['Date'] = date_hdr
        stage = getattr(settings, 'HIKCENTRAL_STAGE', '')
        if stage:
            headers['X-Ca-Stage'] = stage
        if content_md5:
            headers['Content-MD5'] = content_md5

        try:
            if getattr(settings, 'HIKCENTRAL_DEBUG_SIGN', False):
                logger.debug('[Artemis] stringToSign=%s', string_to_sign)
                logger.debug('[Artemis] headers=%s', headers)
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=15)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, params=params, data=body_bytes, timeout=20)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, params=params, data=body_bytes, timeout=20)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, params=params, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"HikCentral API request failed: {e}")
            raise


class HikSession:
    def __init__(self, device: HikDevice):
        self.device = device
        self.base = f"http://{device.host}:{device.port}"
        self.auth = HTTPDigestAuth(device.username, device.password)
        self.verify = device.verify_ssl
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = self.verify
        logger.info(f"HikSession initialized for {device.host}")

    def _make_request(self, method: str, endpoint: str, data: str = None, headers: Dict[str, str] = None) -> requests.Response:
        """Выполняет HTTP запрос к устройству Hikvision"""
        url = f"{self.base}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/xml; charset=UTF-8',
            'Accept': 'application/xml'
        }
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=default_headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, data=data, headers=default_headers, timeout=10)
            elif method.upper() == 'PUT':
                response = self.session.put(url, data=data, headers=default_headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=default_headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Hikvision API request failed: {e}")
            raise

    def get(self, path: str, **kw) -> requests.Response:
        return self._make_request('GET', path)

    def post(self, path: str, data: str = None, **kw) -> requests.Response:
        return self._make_request('POST', path, data=data)

    def put(self, path: str, data: str = None, **kw) -> requests.Response:
        return self._make_request('PUT', path, data=data)


def ensure_person(session: HikSession, employee_no: str, name: str, valid_from: Optional[str], valid_to: Optional[str]) -> str:
    """Создает или обновляет пользователя в системе Hikvision через ISAPI"""
    logger.info(f"Hikvision: Ensuring person {name} ({employee_no}) via ISAPI")
    
    # Формируем XML для создания/обновления пользователя
    person_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<UserInfo>
    <employeeNo>{employee_no}</employeeNo>
    <name>{name}</name>
    <userType>normal</userType>
    <localRight>1</localRight>
    <maxOpenDoorTime>0</maxOpenDoorTime>
    <Valid>
        <enable>true</enable>
        <beginTime>{valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</beginTime>
        <endTime>{valid_to or (datetime.now().replace(year=datetime.now().year + 1)).strftime('%Y-%m-%dT%H:%M:%S')}</endTime>
    </Valid>
</UserInfo>"""
    
    try:
        # Проверяем, существует ли пользователь
        check_response = session.get(f'/ISAPI/AccessControl/UserInfo/{employee_no}')
        
        if check_response.status_code == 200:
            # Пользователь существует, обновляем
            response = session.put(f'/ISAPI/AccessControl/UserInfo/{employee_no}', data=person_xml)
            logger.info(f"Hikvision: Updated existing person {employee_no}")
        else:
            # Пользователь не существует, создаем
            response = session.post('/ISAPI/AccessControl/UserInfo', data=person_xml)
            logger.info(f"Hikvision: Created new person {employee_no}")
        
        return employee_no
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to ensure person {employee_no}: {e}")
        # Возвращаем employee_no как person_id даже при ошибке
        return employee_no


def upload_face(session: HikSession, face_lib_id: str, image_bytes: bytes, person_id: str) -> str:
    """Загружает фото лица в библиотеку лиц Hikvision через ISAPI"""
    logger.info(f"Hikvision: Uploading face for person {person_id} to library {face_lib_id}")
    
    try:
        # Кодируем изображение в base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Формируем XML для загрузки лица
        face_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FaceDataRecord>
    <faceLibType>blackFD</faceLibType>
    <fdId>{face_lib_id}</fdId>
    <faceId>{person_id}</faceId>
    <faceData>{image_base64}</faceData>
</FaceDataRecord>"""
        
        response = session.post('/ISAPI/Intelligent/FDLib/FaceDataRecord', data=face_xml)
        
        if response.status_code in [200, 201]:
            logger.info(f"Hikvision: Successfully uploaded face for person {person_id}")
            return f"face_{person_id}"
        else:
            logger.warning(f"Hikvision: Face upload returned status {response.status_code}")
            return person_id + ":face"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload face for person {person_id}: {e}")
        return person_id + ":face"


def assign_access(session: HikSession, person_id: str, door_ids: List[str], valid_from: Optional[str], valid_to: Optional[str]) -> None:
    """Назначает доступ к дверям для пользователя через ISAPI"""
    logger.info(f"Hikvision: Assigning access for person {person_id} to doors {door_ids}")
    
    try:
        for door_id in door_ids:
            # Формируем XML для назначения прав доступа
            access_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<DoorRight>
    <employeeNo>{person_id}</employeeNo>
    <doorNo>{door_id}</doorNo>
    <planTemplateNo>1</planTemplateNo>
    <valid>
        <enable>true</enable>
        <beginTime>{valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</beginTime>
        <endTime>{valid_to or (datetime.now().replace(year=datetime.now().year + 1)).strftime('%Y-%m-%dT%H:%M:%S')}</endTime>
    </valid>
</DoorRight>"""
            
            response = session.post('/ISAPI/AccessControl/DoorRight', data=access_xml)
            
            if response.status_code in [200, 201]:
                logger.info(f"Hikvision: Successfully assigned access for person {person_id} to door {door_id}")
            else:
                logger.warning(f"Hikvision: Access assignment returned status {response.status_code} for door {door_id}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to assign access for person {person_id}: {e}")


def revoke_access(session: HikSession, person_id: str, door_ids: List[str]) -> None:
    """Отзывает доступ к дверям для пользователя через ISAPI"""
    logger.info(f"Hikvision: Revoking access for person {person_id} from doors {door_ids}")
    
    try:
        for door_id in door_ids:
            # Удаляем права доступа
            response = session._make_request('DELETE', f'/ISAPI/AccessControl/DoorRight/{person_id}/{door_id}')
            
            if response.status_code in [200, 204]:
                logger.info(f"Hikvision: Successfully revoked access for person {person_id} from door {door_id}")
            else:
                logger.warning(f"Hikvision: Access revocation returned status {response.status_code} for door {door_id}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to revoke access for person {person_id}: {e}")


def ensure_person_hikcentral(session: HikCentralSession, employee_no: str, name: str, valid_from: Optional[str], valid_to: Optional[str]) -> str:
    """Создает или обновляет пользователя через HikCentral OpenAPI"""
    logger.info(f"HikCentral: Ensuring person {name} ({employee_no}) via OpenAPI")
    
    try:
        # Проверяем, существует ли пользователь
        response = session._make_request('GET', f'/artemis/api/resource/v1/person', 
                                       params={'personId': employee_no})
        
        if response.status_code == 200:
            # Пользователь существует, обновляем
            person_data = {
                'personId': employee_no,
                'personName': name,
                'orgIndexCode': '1',  # Организация по умолчанию
                'createTime': valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'updateTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'valid': True
            }
            response = session._make_request('PUT', f'/artemis/api/resource/v1/person/{employee_no}', 
                                           data=person_data)
            logger.info(f"HikCentral: Updated existing person {employee_no}")
        else:
            # Пользователь не существует, создаем
            person_data = {
                'personId': employee_no,
                'personName': name,
                'orgIndexCode': '1',  # Организация по умолчанию
                'createTime': valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'valid': True
            }
            response = session._make_request('POST', '/artemis/api/resource/v1/person', 
                                           data=person_data)
            logger.info(f"HikCentral: Created new person {employee_no}")
        
        return employee_no
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to ensure person {employee_no} via HikCentral: {e}")
        return employee_no


def upload_face_hikcentral(session: HikCentralSession, face_lib_id: str, image_bytes: bytes, person_id: str) -> str:
    """Загружает фото лица через HikCentral OpenAPI"""
    logger.info(f"HikCentral: Uploading face for person {person_id} to library {face_lib_id}")
    
    try:
        # Кодируем изображение в base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        face_data = {
            'faceLibType': 'blackFD',
            'fdId': face_lib_id,
            'faceId': person_id,
            'faceData': image_base64
        }
        
        response = session._make_request('POST', '/artemis/api/intelligent/v1/face/picture', 
                                       data=face_data)
        
        if response.status_code in [200, 201]:
            logger.info(f"HikCentral: Successfully uploaded face for person {person_id}")
            return f"face_{person_id}"
        else:
            logger.warning(f"HikCentral: Face upload returned status {response.status_code}")
            return person_id + ":face"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload face for person {person_id} via HikCentral: {e}")
        return person_id + ":face"


def assign_access_hikcentral(session: HikCentralSession, person_id: str, door_ids: List[str], valid_from: Optional[str], valid_to: Optional[str]) -> None:
    """Назначает доступ к дверям через HikCentral OpenAPI"""
    logger.info(f"HikCentral: Assigning access for person {person_id} to doors {door_ids}")
    
    try:
        for door_id in door_ids:
            access_data = {
                'personId': person_id,
                'doorIndexCodes': [door_id],
                'planTemplateId': '1',  # Шаблон доступа по умолчанию
                'valid': True,
                'beginTime': valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'endTime': valid_to or (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
            }
            
            response = session._make_request('POST', '/artemis/api/acs/v1/door/rights', 
                                           data=access_data)
            
            if response.status_code in [200, 201]:
                logger.info(f"HikCentral: Successfully assigned access for person {person_id} to door {door_id}")
            else:
                logger.warning(f"HikCentral: Access assignment returned status {response.status_code} for door {door_id}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to assign access for person {person_id} via HikCentral: {e}")


def revoke_access_hikcentral(session: HikCentralSession, person_id: str, door_ids: List[str]) -> None:
    """Отзывает доступ к дверям через HikCentral OpenAPI"""
    logger.info(f"HikCentral: Revoking access for person {person_id} from doors {door_ids}")
    
    try:
        for door_id in door_ids:
            response = session._make_request('DELETE', f'/artemis/api/acs/v1/door/rights/{person_id}/{door_id}')
            
            if response.status_code in [200, 204]:
                logger.info(f"HikCentral: Successfully revoked access for person {person_id} from door {door_id}")
            else:
                logger.warning(f"HikCentral: Access revocation returned status {response.status_code} for door {door_id}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to revoke access for person {person_id} via HikCentral: {e}")


def test_hikcentral_connection(server: HikCentralServer) -> Dict[str, Any]:
    """Тестирует подключение к HikCentral серверу"""
    logger.info(f"Testing connection to HikCentral server {server.name}")
    
    try:
        session = HikCentralSession(server)
        
        # Пробуем получить информацию о сервере
        response = session._make_request('GET', '/artemis/api/common/v1/version')
        
        if response.status_code == 200:
            version_data = response.json()
            server_info = {
                'status': 'success',
                'name': server.name,
                'base_url': server.base_url,
                'version': version_data.get('version', 'Unknown'),
                'build_time': version_data.get('buildTime', 'Unknown')
            }
            logger.info(f"HikCentral server {server.name} connection successful")
            return server_info
        else:
            return {
                'status': 'error',
                'name': server.name,
                'error': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        logger.error(f"Failed to test connection to HikCentral server {server.name}: {e}")
        return {
            'status': 'error',
            'name': server.name,
            'error': str(e)
        }


def test_device_connection(device: HikDevice) -> Dict[str, Any]:
    """Тестирует подключение к устройству Hikvision"""
    logger.info(f"Testing connection to Hikvision device {device.host}")
    
    try:
        session = HikSession(device)
        
        # Пробуем получить информацию об устройстве
        response = session.get('/ISAPI/System/deviceInfo')
        
        if response.status_code == 200:
            # Парсим XML ответ
            root = ET.fromstring(response.text)
            device_info = {
                'status': 'success',
                'host': device.host,
                'model': root.find('.//modelName').text if root.find('.//modelName') is not None else 'Unknown',
                'firmware': root.find('.//firmwareVersion').text if root.find('.//firmwareVersion') is not None else 'Unknown',
                'serial': root.find('.//serialNumber').text if root.find('.//serialNumber') is not None else 'Unknown'
            }
            logger.info(f"Hikvision device {device.host} connection successful")
            return device_info
        else:
            return {
                'status': 'error',
                'host': device.host,
                'error': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        logger.error(f"Failed to test connection to device {device.host}: {e}")
        return {
            'status': 'error',
            'host': device.host,
            'error': str(e)
        }


