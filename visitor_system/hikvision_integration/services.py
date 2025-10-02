import base64
import logging
from typing import Any, Dict, List, Optional
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from django.conf import settings
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
        # Всегда задаём Accept явно
        accept = 'application/json'
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
        stage = getattr(settings, 'HIKCENTRAL_STAGE', '')
        if stage:
            headers_for_sign['x-ca-stage'] = stage
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

    def _make_multipart_request(self, method: str, endpoint: str, files: Dict, fields: Dict = None, params: Dict = None) -> requests.Response:
        """Выполняет multipart/form-data запрос с подписью AK/SK.
        
        Args:
            method: HTTP метод (POST, PUT)
            endpoint: API endpoint
            files: Словарь файлов {'field_name': ('filename', bytes, 'mime_type')}
            fields: Дополнительные поля формы (опционально)
            params: Query параметры (опционально)
            
        Returns:
            Response object
            
        Example:
            session._make_multipart_request(
                'POST',
                '/artemis/api/common/v1/picture/upload',
                files={'file': ('photo.jpg', image_bytes, 'image/jpeg')},
                fields={'type': '1'}
            )
        """
        from urllib.parse import urlencode
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        
        logger.info(f"HikCentral: Making multipart request to {endpoint}")
        
        # Собираем URL и URI+query
        url = f"{self.base_url}{endpoint}"
        query_str = urlencode(params or {}, doseq=True)
        uri_with_query = endpoint + (f"?{query_str}" if query_str else '')
        
        # Создаём multipart payload
        multipart_fields = {}
        if fields:
            multipart_fields.update(fields)
        if files:
            for field_name, file_tuple in files.items():
                # file_tuple: (filename, bytes, mime_type)
                import io
                if isinstance(file_tuple[1], bytes):
                    multipart_fields[field_name] = (file_tuple[0], io.BytesIO(file_tuple[1]), file_tuple[2])
                else:
                    multipart_fields[field_name] = file_tuple
        
        multipart = MultipartEncoder(fields=multipart_fields)
        body_bytes = multipart.to_string()
        
        # Content-Type для multipart включает boundary
        content_type = multipart.content_type
        content_md5 = self._calc_content_md5(body_bytes)
        accept = 'application/json'
        
        # Управляем включением Date через настройки
        import time, uuid, email.utils
        date_hdr = email.utils.formatdate(usegmt=True) if getattr(settings, 'HIKCENTRAL_INCLUDE_DATE', False) else None
        x_ca_timestamp = str(int(time.time() * 1000))
        x_ca_nonce = str(uuid.uuid4())
        
        # Заголовки для подписи
        headers_for_sign = {
            'x-ca-key': self.server.integration_key,
            'x-ca-timestamp': x_ca_timestamp,
            'x-ca-nonce': x_ca_nonce,
        }
        stage = getattr(settings, 'HIKCENTRAL_STAGE', '')
        if stage:
            headers_for_sign['x-ca-stage'] = stage
        
        signed_names, headers_block = self._canonical_headers(headers_for_sign)
        
        # Строка для подписи
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
        
        # Финальные заголовки
        headers = {
            'Accept': accept,
            'Content-Type': content_type,
            'Content-MD5': content_md5,
            'X-Ca-Key': self.server.integration_key,
            'X-Ca-Timestamp': x_ca_timestamp,
            'X-Ca-Nonce': x_ca_nonce,
            'X-Ca-Signature-Headers': signed_names,
            'X-Ca-Signature': signature,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if date_hdr:
            headers['Date'] = date_hdr
        if stage:
            headers['X-Ca-Stage'] = stage
        
        try:
            if getattr(settings, 'HIKCENTRAL_DEBUG_SIGN', False):
                logger.debug('[Artemis Multipart] stringToSign=%s', string_to_sign)
                logger.debug('[Artemis Multipart] headers=%s', headers)
                logger.debug('[Artemis Multipart] body size=%d', len(body_bytes))
            
            if method.upper() == 'POST':
                response = self.session.post(url, headers=headers, params=params, data=body_bytes, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, params=params, data=body_bytes, timeout=30)
            else:
                raise ValueError(f"Multipart only supports POST/PUT, got: {method}")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HikCentral multipart request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
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
    """Загружает фото лица в библиотеку лиц Hikvision через ISAPI.
    
    Сначала пытается загрузить фото напрямую к персоне через /ISAPI/Intelligent/FDLib/picture,
    затем пробует старый метод через FaceDataRecord если первый не сработал.
    """
    logger.info(f"Hikvision ISAPI: Uploading face for person {person_id} to library {face_lib_id}")
    
    try:
        # Метод 1: Прямая загрузка фото к персоне (современный ISAPI)
        # Multipart form-data с бинарным изображением
        import io
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        
        # Создаем multipart с изображением
        multipart_data = MultipartEncoder(
            fields={
                'FaceDataRecord': (
                    'face.jpg',
                    io.BytesIO(image_bytes),
                    'image/jpeg'
                )
            }
        )
        
        # Пытаемся загрузить через /ISAPI/Intelligent/FDLib/picture
        headers = {'Content-Type': multipart_data.content_type}
        url = f'/ISAPI/Intelligent/FDLib/FaceDataRecord/picture?format=json&FDID={face_lib_id}&faceID={person_id}'
        
        try:
            response = session._make_request('PUT', url, data=multipart_data.to_string(), headers=headers)
            if response.status_code in [200, 201]:
                logger.info(f"Hikvision ISAPI: Successfully uploaded face via PUT /picture for person {person_id}")
                return f"face_{person_id}"
            else:
                logger.warning(f"Hikvision ISAPI: PUT /picture returned status {response.status_code}, trying POST method")
        except Exception as e:
            logger.warning(f"Hikvision ISAPI: PUT /picture failed ({e}), trying POST method")
        
        # Метод 2: POST с base64 (старый метод, fallback)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # XML payload для FaceDataRecord
        face_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FaceDataRecord>
    <faceLibType>blackFD</faceLibType>
    <FDID>{face_lib_id}</FDID>
    <faceID>{person_id}</faceID>
    <faceData>{image_base64}</faceData>
</FaceDataRecord>"""
        
        response = session.post('/ISAPI/Intelligent/FDLib/FaceDataRecord', data=face_xml)
        
        if response.status_code in [200, 201]:
            logger.info(f"Hikvision ISAPI: Successfully uploaded face via POST XML for person {person_id}")
            return f"face_{person_id}"
        else:
            logger.warning(f"Hikvision ISAPI: Face upload XML returned status {response.status_code}")
            # Пробуем альтернативный endpoint
            response_alt = session.post(f'/ISAPI/Intelligent/FDLib/FDSetUp/picture?format=json&FDID={face_lib_id}', 
                                       data=image_bytes,
                                       headers={'Content-Type': 'application/octet-stream'})
            if response_alt.status_code in [200, 201]:
                logger.info(f"Hikvision ISAPI: Successfully uploaded via FDSetUp/picture for person {person_id}")
                return f"face_{person_id}"
            
            return f"face_{person_id}_status_{response.status_code}"
            
    except Exception as e:
        logger.error(f"Hikvision ISAPI: Failed to upload face for person {person_id}: {e}")
        return f"face_{person_id}_error"


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


def find_org_by_name(session: HikCentralSession, org_name: str) -> Optional[str]:
    """Находит организацию в HCP по названию и возвращает её orgIndexCode.
    Использует API: POST /artemis/api/resource/v1/org/advance/orgList
    """
    logger.info("HikCentral: Searching for organization '%s'", org_name)
    try:
        # Поиск организации по имени (fuzzy search поддерживается)
        payload = {
            'pageNo': 1,
            'pageSize': 100,
            'orgName': org_name
        }
        resp = session._make_request('POST', '/artemis/api/resource/v1/org/advance/orgList', data=payload)
        result = resp.json()
        
        if isinstance(result, dict) and result.get('code') == '0':
            orgs = result.get('data', {}).get('list', [])
            # Ищем точное совпадение или первую подходящую
            for org in orgs:
                if org.get('orgName', '').strip().lower() == org_name.strip().lower():
                    org_index = org.get('orgIndexCode', org.get('indexCode'))
                    logger.info("HikCentral: Found exact match organization '%s' with orgIndexCode=%s", org_name, org_index)
                    return str(org_index)
            
            # Если точного совпадения нет, берём первую
            if orgs:
                org_index = orgs[0].get('orgIndexCode', orgs[0].get('indexCode'))
                logger.info("HikCentral: Found partial match organization '%s' with orgIndexCode=%s", orgs[0].get('orgName'), org_index)
                return str(org_index)
        
        logger.warning("HikCentral: Organization '%s' not found, code=%s", org_name, result.get('code'))
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error("Failed to search organization '%s': %s", org_name, e)
        return None


def ensure_person_hikcentral(session: HikCentralSession, employee_no: str, name: str, valid_from: Optional[str], valid_to: Optional[str]) -> str:
    """Создаёт/обновляет персону в HCP, используя personCode=наш guest_id и возвращает реальный personId.
    Логика:
    - ищем по personCode (/resource/v1/person/personCode/personInfo)
    - если есть — при необходимости обновляем сроки begin/end
    - если нет — создаём через /resource/v1/person/single/add c personCode и получаем personId повторным запросом
    
    Автоматически назначает организацию из HIKCENTRAL_ORG_NAME если она найдена в HCP.
    """
    logger.info("HikCentral: ensure person by personCode=%s name=%s", employee_no, name)
    
    # Определяем orgIndexCode: сначала пытаемся найти организацию по имени
    default_org = getattr(settings, 'HIKCENTRAL_DEFAULT_ORG_INDEX', '1')
    org_name = getattr(settings, 'HIKCENTRAL_ORG_NAME', '')
    
    if org_name:
        # Пытаемся найти организацию по имени
        found_org = find_org_by_name(session, org_name)
        if found_org:
            default_org = found_org
            logger.info("HikCentral: Using organization '%s' with orgIndexCode=%s", org_name, default_org)
        else:
            logger.warning("HikCentral: Organization '%s' not found, using default orgIndexCode=%s", org_name, default_org)
    try:
        # Ищем по personCode
        lookup_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personCode/personInfo', data={
            'personCode': str(employee_no)
        })
        try:
            lookup_json = lookup_resp.json()
            logger.info("HikCentral: lookup personCode=%s response=%s", employee_no, lookup_json)
        except Exception as e:
            logger.error("HikCentral: Failed to parse lookup response: %s", e)
            lookup_json = {}

        import pytz
        
        # Нормализуем даты в формате, который ожидает HikCentral
        # HikCentral требует формат ISO 8601 с указанием часового пояса
        # например: '2025-09-19T15:17:39+05:00'
        def format_datetime_for_hikcentral(dt):
            # Преобразуем строку в datetime, если нужно
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except ValueError:
                    dt = datetime.now()
                    
            # Добавляем часовой пояс, если его нет
            if dt.tzinfo is None:
                dt = pytz.timezone('Asia/Almaty').localize(dt)
                
            # Форматируем дату в нужный формат с двоеточием в часовом поясе
            formatted = dt.strftime('%Y-%m-%dT%H:%M:%S%z')
            # Вставляем двоеточие в часовой пояс: +0500 -> +05:00
            return formatted[:-2] + ':' + formatted[-2:]
        
        # Форматируем даты начала и окончания
        now_s = format_datetime_for_hikcentral(datetime.now())
        begin_s = format_datetime_for_hikcentral(valid_from) if valid_from else now_s
        end_s = format_datetime_for_hikcentral(valid_to) if valid_to else format_datetime_for_hikcentral(datetime.now() + timedelta(days=3650))

        if isinstance(lookup_json, dict) and lookup_json.get('code') == '0' and lookup_json.get('data'):
            person = lookup_json['data']
            person_id = str(person.get('personId'))
            # Обновляем сроки/имя при необходимости
            # Если включён форсинг отдела, всегда проставляем orgIndexCode из настроек
            force_org = getattr(settings, 'HIKCENTRAL_FORCE_ORG', False)
            
            # Используем найденную организацию или существующую
            target_org = default_org if force_org else (person.get('orgIndexCode') or default_org)
            
            payload = {
                'personId': person_id,
                'personName': name,
                'orgIndexCode': target_org,
                'beginTime': begin_s,
                'endTime': end_s,
            }
            update_resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/update', data=payload)
            update_json = update_resp.json()
            logger.info("HikCentral: person update response=%s", update_json)
            logger.info("HikCentral: person updated personCode=%s personId=%s orgIndexCode=%s", employee_no, person_id, target_org)
            return person_id

        # Не нашли — создаём по personCode (без жёсткой фиксации personId)
        # Разделяем полное имя на имя и фамилию (предполагаем формат "Фамилия Имя")
        name_parts = name.split(maxsplit=1)
        person_family_name = name_parts[0] if len(name_parts) > 0 else name
        person_given_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Используем найденную ранее организацию
        payload_add = {
            'personName': name,
            'personFamilyName': person_family_name,
            'personGivenName': person_given_name,
            'personCode': str(employee_no),
            'orgIndexCode': default_org,
            'beginTime': begin_s,
            'endTime': end_s,
        }
        logger.info("HikCentral: person add payload=%s orgIndexCode=%s", payload_add, default_org)
        add_resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/add', data=payload_add)
        add_json = add_resp.json()
        logger.info("HikCentral: person add response=%s", add_json)
        logger.info("HikCentral: person add by personCode=%s HTTP=%s", employee_no, add_resp.status_code)
        
        # Получаем personId из ответа, если он там есть
        person_id = ''
        if isinstance(add_json, dict) and add_json.get('code') == '0' and add_json.get('data'):
            # В некоторых версиях HCP 'data' может быть строкой (сам personId) или объектом {personId: ...}
            if isinstance(add_json['data'], dict):
                person_id = str(add_json['data'].get('personId') or '')
            else:
                person_id = str(add_json['data'])
            if person_id:
                logger.info("HikCentral: personId=%s received from add response", person_id)
                return person_id

        # Повторный поиск, чтобы получить выданный HCP personId
        lookup_resp2 = session._make_request('POST', '/artemis/api/resource/v1/person/personCode/personInfo', data={
            'personCode': str(employee_no)
        })
        try:
            j2 = lookup_resp2.json()
            logger.info("HikCentral: second lookup personCode=%s response=%s", employee_no, j2)
            if isinstance(j2, dict) and j2.get('code') == '0' and j2.get('data'):
                person_id = str(j2['data'].get('personId') or '')
                logger.info("HikCentral: personId=%s received from second lookup", person_id)
        except Exception as e:
            logger.error("HikCentral: Failed to parse second lookup response: %s", e)
            person_id = ''
            
        if not person_id:
            # Если всё еще нет personId, поищем через advance/personList
            try:
                search_resp = session._make_request('POST', '/artemis/api/resource/v1/person/advance/personList', data={
                    'pageNo': 1,
                    'pageSize': 100,
                    'personCode': str(employee_no)
                })
                search_json = search_resp.json()
                logger.info("HikCentral: advance search for personCode=%s response=%s", employee_no, search_json)
                if isinstance(search_json, dict) and search_json.get('code') == '0':
                    persons = search_json.get('data', {}).get('list', [])
                    for p in persons:
                        if str(p.get('personCode')) == str(employee_no):
                            person_id = str(p.get('personId') or '')
                            logger.info("HikCentral: personId=%s found in advance search", person_id)
                            break
            except Exception as e:
                logger.error("HikCentral: Failed to perform advance search: %s", e)
                
        return person_id or str(employee_no)

    except requests.exceptions.RequestException as e:
        logger.error("Failed to ensure person by personCode=%s: %s", employee_no, e)
        return str(employee_no)


def ensure_face_group(session: HikCentralSession, group_name: str = "Guests") -> Optional[str]:
    """Находит или создает Face Group для гостей в HCP.
    
    Сначала ищет группу по имени, затем пробует использовать настройку HIKCENTRAL_FACE_GROUP_INDEX_CODE,
    если она не установлена - использует первую доступную группу.
    
    Args:
        session: Сессия HikCentral
        group_name: Название группы (по умолчанию "Guests")
        
    Returns:
        groupId найденной группы, или None при ошибке
    """
    from django.conf import settings
    
    logger.info("HikCentral: Ensuring Face Group '%s'", group_name)
    
    try:
        # Ищем существующую группу
        search_resp = session._make_request('POST', '/artemis/api/frs/v1/face/group', data={
            'pageNo': 1,
            'pageSize': 100
        })
        search_json = search_resp.json()
        
        if search_json.get('code') == '0' and search_json.get('data'):
            groups = search_json['data'].get('list', [])
            
            # Сначала ищем по имени
            for group in groups:
                if group.get('groupName') == group_name:
                    group_id = group.get('groupId')
                    logger.info("HikCentral: Found Face Group '%s' with ID=%s", group_name, group_id)
                    return str(group_id)
            
            # Проверяем настройку HIKCENTRAL_FACE_GROUP_INDEX_CODE
            configured_group_id = getattr(settings, 'HIKCENTRAL_FACE_GROUP_INDEX_CODE', '')
            if configured_group_id:
                logger.info("HikCentral: Using configured Face Group ID=%s", configured_group_id)
                return str(configured_group_id)
            
            # Используем первую доступную группу
            if groups:
                first_group = groups[0]
                group_id = first_group.get('groupId')
                group_name_found = first_group.get('groupName', 'Unknown')
                logger.info("HikCentral: Using first available Face Group '%s' with ID=%s", group_name_found, group_id)
                return str(group_id)
        
        # Нет доступных групп - пытаемся создать
        logger.warning("HikCentral: No Face Groups found, attempting to create '%s'", group_name)
        create_resp = session._make_request('POST', '/artemis/api/frs/v1/face/group/single/addition', data={
            'name': group_name,
            'type': '1'
        })
        create_json = create_resp.json()
        
        if create_json.get('code') == '0' and create_json.get('data'):
            group_id = create_json['data'].get('groupId')
            logger.info("HikCentral: Created Face Group '%s' with ID=%s", group_name, group_id)
            return str(group_id)
        else:
            logger.error("HikCentral: Failed to create Face Group: %s (no permission or API limitation)", create_json.get('msg'))
            return None
            
    except Exception as e:
        logger.error("HikCentral: Error ensuring Face Group: %s", e)
        return None


def upload_face_with_validation(session: HikCentralSession, image_bytes: bytes, person_id: str, person_code: str) -> bool:
    """Загрузка фото через faceCheck + person/single/update.
    
    Двухшаговый процесс:
    1. faceCheck - валидация фото на ACS устройстве
    2. person/single/update - загрузка валидированного фото с полными данными Person
    
    Args:
        session: Сессия HikCentral
        image_bytes: Байты изображения
        person_id: ID Person в HCP
        person_code: Код Person (обычно guest_id)
        
    Returns:
        True если успешно, False если ошибка
    """
    logger.info("HikCentral: Uploading face with validation for person %s (size: %d bytes)", person_id, len(image_bytes))
    
    try:
        # Шаг 0: Получаем информацию о Person
        logger.info("HikCentral: Step 0 - Getting person info")
        person_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
            'personId': str(person_id)
        })
        person_json = person_resp.json()
        
        if not (isinstance(person_json, dict) and person_json.get('code') == '0' and person_json.get('data')):
            logger.error("HikCentral: Failed to get person info: %s", person_json.get('msg'))
            return False
            
        person_data = person_json['data']
        logger.info("HikCentral: Person: %s (orgIndexCode=%s)", 
                   person_data.get('personName'), person_data.get('orgIndexCode'))
        
        # Шаг 1: Получаем ACS устройство
        logger.info("HikCentral: Step 1 - Getting ACS device")
        acs_resp = session._make_request('POST', '/artemis/api/resource/v1/acsDevice/acsDeviceList', data={
            'pageNo': 1,
            'pageSize': 10
        })
        acs_json = acs_resp.json()
        
        acs_devices = acs_json.get('data', {}).get('list', [])
        if not acs_devices:
            logger.error("HikCentral: No ACS devices found")
            return False
        
        # Используем первое активное устройство
        acs_device = next((d for d in acs_devices if d.get('status') == 1), acs_devices[0])
        acs_dev_index_code = acs_device['acsDevIndexCode']
        logger.info("HikCentral: Using ACS device: %s (indexCode=%s)", 
                   acs_device.get('acsDevName'), acs_dev_index_code)
        
        # Шаг 2: faceCheck - валидация фото
        logger.info("HikCentral: Step 2 - Validating face with faceCheck")
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        facecheck_payload = {
            'userId': person_code,  # personCode
            'faceData': image_base64,
            'acsDevIndexCode': acs_dev_index_code
        }
        
        facecheck_resp = session._make_request('POST', '/artemis/api/acs/v1/faceCheck', data=facecheck_payload)
        facecheck_json = facecheck_resp.json()
        
        logger.info("HikCentral: faceCheck response code=%s msg=%s", 
                   facecheck_json.get('code'), facecheck_json.get('msg'))
        
        if facecheck_json.get('code') != '0':
            logger.error("HikCentral: Face validation failed: %s", facecheck_json.get('msg'))
            return False
        
        logger.info("HikCentral: Face validation SUCCESS!")
        
        # Шаг 3: person/single/update с ПОЛНЫМИ данными
        logger.info("HikCentral: Step 3 - Uploading validated face to Person")
        
        # Обновляем Person с фото и ВСЕМИ существующими данными
        update_payload = {
            'personId': str(person_id),
            'personCode': person_code,
            'personName': person_data.get('personName', f'Guest_{person_code}'),
            'orgIndexCode': person_data.get('orgIndexCode'),
            'gender': person_data.get('gender', '0'),
            'phoneNo': person_data.get('phoneNo', ''),
            'email': person_data.get('email', ''),
            'personPhoto': image_base64  # Валидированное фото
        }
        
        update_resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=update_payload)
        update_json = update_resp.json()
        
        logger.info("HikCentral: person/single/update response code=%s msg=%s",
                   update_json.get('code'), update_json.get('msg'))
        
        if update_json.get('code') != '0':
            logger.error("HikCentral: Failed to update person with photo: %s", update_json.get('msg'))
            return False
        
        logger.info("HikCentral: Person updated with validated face!")
        
        # Шаг 4: Применяем изменения на устройства
        try:
            logger.info("HikCentral: Step 4 - Applying changes to devices")
            reapply_resp = session._make_request('POST', '/artemis/api/visitor/v1/auth/reapplication', data={
                'personIds': [str(person_id)]
            })
            reapply_json = reapply_resp.json()
            logger.info("HikCentral: auth/reapplication response code=%s msg=%s",
                       reapply_json.get('code'), reapply_json.get('msg'))
        except Exception as e:
            logger.warning("HikCentral: Failed to apply changes to devices: %s", e)
        
        logger.info("HikCentral: Face upload with validation completed successfully!")
        return True
        
    except Exception as e:
        logger.error("HikCentral: Failed to upload face with validation: %s", e)
        import traceback
        traceback.print_exc()
        return False


def upload_face_hikcentral_multipart(session: HikCentralSession, face_lib_id: str, image_bytes: bytes, person_id: str) -> str:
    """Загрузка фото через multipart/form-data upload (РЕКОМЕНДУЕМЫЙ МЕТОД).
    
    Использует правильный REST-подход с multipart/form-data для загрузки файлов.
    
    Процесс:
    1. Загружаем фото на /common/v1/picture/upload (получаем picUri)
    2. Привязываем picUri к Person через /person/single/update
    3. Применяем изменения на устройства
    
    Args:
        session: Сессия HikCentral
        face_lib_id: Не используется (для совместимости)
        image_bytes: Байты изображения
        person_id: ID Person в HCP
        
    Returns:
        faceId/picUri загруженного фото
    """
    logger.info("HikCentral: Uploading face via multipart for person %s (size: %d bytes)", person_id, len(image_bytes))
    
    try:
        # Шаг 1: Получаем информацию о Person
        logger.info("HikCentral: Step 1 - Getting person info")
        person_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
            'personId': str(person_id)
        })
        person_json = person_resp.json()
        
        if not (isinstance(person_json, dict) and person_json.get('code') == '0' and person_json.get('data')):
            logger.error("HikCentral: Failed to get person info: %s", person_json.get('msg'))
            return f"face_{person_id}"
            
        person_data = person_json['data']
        person_name = person_data.get('personName', 'Guest')
        org_index = person_data.get('orgIndexCode', '1')
        logger.info("HikCentral: Person: %s (org=%s)", person_name, org_index)
        
        # Шаг 2: Оптимизируем изображение
        logger.info("HikCentral: Step 2 - Optimizing image")
        from PIL import Image
        import io
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            max_size = (800, 800)
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            image_bytes = buffer.getvalue()
            logger.info("HikCentral: Image optimized: %d bytes", len(image_bytes))
        except Exception as e:
            logger.warning("HikCentral: Failed to optimize image, using original: %s", e)
        
        # Шаг 3: Загружаем фото через multipart
        logger.info("HikCentral: Step 3 - Uploading photo via multipart")
        
        # Пробуем разные endpoints по приоритету
        endpoints = [
            '/artemis/api/common/v1/picture/upload',
            '/artemis/api/resource/v1/person/photo',
        ]
        
        pic_uri = None
        for endpoint in endpoints:
            try:
                logger.info("HikCentral: Trying endpoint %s", endpoint)
                upload_resp = session._make_multipart_request(
                    'POST',
                    endpoint,
                    files={'file': ('photo.jpg', image_bytes, 'image/jpeg')},
                    fields={'type': '1'} if 'common' in endpoint else {'personId': str(person_id)}
                )
                
                upload_json = upload_resp.json()
                logger.info("HikCentral: Upload response code=%s msg=%s", upload_json.get('code'), upload_json.get('msg'))
                
                if upload_json.get('code') == '0':
                    # Успешная загрузка
                    data = upload_json.get('data', {})
                    pic_uri = data.get('picUri', '') if isinstance(data, dict) else ''
                    
                    if pic_uri:
                        logger.info("HikCentral: Successfully uploaded photo, picUri=%s", pic_uri)
                        break
                    else:
                        logger.warning("HikCentral: Upload success but no picUri in response")
                else:
                    logger.warning("HikCentral: Upload failed with code=%s msg=%s", upload_json.get('code'), upload_json.get('msg'))
                    
            except Exception as e:
                logger.warning("HikCentral: Endpoint %s failed: %s", endpoint, e)
                continue
        
        # Если не получили picUri, возвращаемся к старому методу
        if not pic_uri:
            logger.warning("HikCentral: All multipart endpoints failed, falling back to JSON method")
            return upload_face_hikcentral(session, face_lib_id, image_bytes, person_id)
        
        # Шаг 4: Привязываем фото к Person
        logger.info("HikCentral: Step 4 - Linking photo to Person")
        
        update_payload = {
            'personId': str(person_id),
            'personName': person_name,
            'orgIndexCode': str(org_index),
            'personPhoto': {
                'picUri': pic_uri
            }
        }
        
        update_resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/update', data=update_payload)
        update_json = update_resp.json()
        logger.info("HikCentral: Link photo response code=%s msg=%s", update_json.get('code'), update_json.get('msg'))
        
        if update_json.get('code') != '0':
            logger.error("HikCentral: Failed to link photo to Person: %s", update_json.get('msg'))
            return f"face_{person_id}"
        
        # Шаг 5: Применяем изменения на устройства
        try:
            logger.info("HikCentral: Step 5 - Applying changes to devices")
            reapply_resp = session._make_request('POST', '/artemis/api/visitor/v1/auth/reapplication', data={
                'personIds': [str(person_id)]
            })
            reapply_json = reapply_resp.json()
            logger.info("HikCentral: auth/reapplication response code=%s msg=%s",
                       reapply_json.get('code'), reapply_json.get('msg'))
        except Exception as e:
            logger.warning("HikCentral: Failed to apply changes to devices: %s", e)
        
        logger.info("HikCentral: Multipart face upload completed successfully for person %s", person_id)
        return pic_uri
        
    except Exception as e:
        logger.error("HikCentral: Multipart upload failed for %s: %s", person_id, e)
        import traceback
        traceback.print_exc()
        # Fallback к старому методу
        logger.info("HikCentral: Falling back to JSON upload method")
        return upload_face_hikcentral(session, face_lib_id, image_bytes, person_id)


def upload_face_hikcentral(session: HikCentralSession, face_lib_id: str, image_bytes: bytes, person_id: str) -> str:
    """Загрузка фото через /person/face/update API (РАБОЧИЙ МЕТОД!).
    
    ВАЖНО: Найден рабочий метод после exhaustive testing!
    Использует /artemis/api/resource/v1/person/face/update с оптимизированным изображением.
    
    Ключевые факторы успеха:
    1. Endpoint: /person/face/update (НЕ /person/single/update!)
    2. Parameters: personId + faceData (только эти два!)
    3. Image optimization: Resize to 500x500, JPEG quality 80
    
    Args:
        session: Сессия HikCentral
        face_lib_id: Не используется (для обратной совместимости)
        image_bytes: Байты изображения
        person_id: ID Person в HCP
        
    Returns:
        picUri загруженного фото или face_id для совместимости
    """
    logger.info("HikCentral: Uploading face for person %s (size: %d bytes) via /person/face/update", person_id, len(image_bytes))
    
    # Проверяем размер изображения
    if len(image_bytes) < 5000:
        logger.warning("HikCentral: Image too small (%d bytes), HCP may reject it. Recommended: >50KB", len(image_bytes))
    
    try:
        # Шаг 1: Получаем информацию о Person
        logger.info("HikCentral: Step 1 - Getting person info for %s", person_id)
        person_resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', data={
            'personId': str(person_id)
        })
        person_json = person_resp.json()
        
        if not (isinstance(person_json, dict) and person_json.get('code') == '0' and person_json.get('data')):
            logger.error("HikCentral: Failed to get person info: %s", person_json.get('msg'))
            return f"face_{person_id}"
            
        person_data = person_json['data']
        person_code = person_data.get('personCode')
        person_name = person_data.get('personName', 'Guest')
        org_index = person_data.get('orgIndexCode', '1')
        logger.info("HikCentral: Person: %s (code=%s, org=%s)", person_name, person_code, org_index)
        
        # Шаг 2: Загружаем фото через person/face/update (РАБОЧИЙ МЕТОД!)
        logger.info("HikCentral: Step 2 - Uploading face via /person/face/update")
        
        # ВАЖНО: Найден РАБОЧИЙ метод после exhaustive testing!
        # Ключевые факторы успеха:
        # 1. Endpoint: /person/face/update (НЕ /person/single/update!)
        # 2. Image optimization: 500x500 pixels работает лучше всего
        # 3. Parameters: ТОЛЬКО personId + faceData (без других полей!)
        
        from PIL import Image
        import io
        
        # Оптимизируем изображение - КРИТИЧНО для успеха!
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Оптимальный размер: 500x500 (протестировано - работает!)
            max_size = (500, 500)
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            # Сохраняем оптимизированное изображение
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=80, optimize=True)
            image_bytes = buffer.getvalue()
            logger.info("HikCentral: Image optimized to 500x500: %d bytes", len(image_bytes))
        except Exception as e:
            logger.warning("HikCentral: Failed to optimize image: %s", e)
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # РАБОЧИЙ payload: ТОЛЬКО personId + faceData!
        # Не добавляйте другие поля - это критично!
        update_payload = {
            'personId': str(person_id),
            'faceData': image_base64  # Используем faceData, а не personPhoto!
        }
        
        # РАБОЧИЙ endpoint: /person/face/update!
        face_resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=update_payload)
        face_json = face_resp.json()
        
        logger.info("HikCentral: person/single/update response code=%s msg=%s", 
                   face_json.get('code'), face_json.get('msg'))
        
        if face_json.get('code') != '0':
            logger.error("HikCentral: Failed to upload face: %s", face_json.get('msg'))
            return f"face_{person_id}_error"
        
        logger.info("HikCentral: Successfully uploaded face for person %s", person_id)
        
        # Шаг 3: Применяем изменения на устройства
        try:
            logger.info("HikCentral: Step 3 - Applying changes to devices via reapplication")
            reapply_resp = session._make_request('POST', '/artemis/api/visitor/v1/auth/reapplication', data={
                'personIds': [str(person_id)]
            })
            reapply_json = reapply_resp.json()
            logger.info("HikCentral: auth/reapplication response code=%s msg=%s",
                       reapply_json.get('code'), reapply_json.get('msg'))
        except Exception as e:
            logger.warning("HikCentral: Failed to apply changes to devices: %s", e)
        
        logger.info("HikCentral: Face upload completed for person %s", person_id)
        return f"face_{person_id}"
        
    except requests.exceptions.RequestException as e:
        logger.error("HikCentral: Failed to upload face for %s: %s", person_id, e)
        return f"face_{person_id}"
    except Exception as e:
        logger.error("HikCentral: Unexpected error uploading face for %s: %s", person_id, e)
        import traceback
        traceback.print_exc()
        return f"face_{person_id}"


def assign_access_hikcentral(session: HikCentralSession, person_id: str, door_ids: List[str], valid_from: Optional[str], valid_to: Optional[str]) -> None:
    """Назначение доступа: /artemis/api/visitor/v1/auth/reapplication (триггер применения на устройства)."""
    logger.info("HikCentral: Reapplying auth for person %s", person_id)
    try:
        payload = {
            'personId': str(person_id)
        }
        resp = session._make_request('POST', '/artemis/api/visitor/v1/auth/reapplication', data=payload)
        logger.info("HikCentral: reapplication HTTP=%s", resp.status_code)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to reapply auth for %s: %s", person_id, e)


def revoke_access_hikcentral(session: HikCentralSession, person_id: str, door_ids: List[str]) -> None:
    """Отзывает доступ к дверям через HikCentral OpenAPI"""
    logger.info(f"HikCentral: Revoking access for person {person_id} from doors {door_ids}")
    
    try:
        for door_id in door_ids:
            response = session._make_request('DELETE', f'/artemis/api/acs/v1/privilege/group/single/addPersons')
            
            if response.status_code in [200, 204]:
                logger.info(f"HikCentral: Successfully revoked access for person {person_id} from door {door_id}")
            else:
                logger.warning(f"HikCentral: Access revocation returned status {response.status_code} for door {door_id}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to revoke access for person {person_id} via HikCentral: {e}")


def upload_face_isapi(device, person_code: str, image_bytes: bytes) -> bool:
    """Загрузка фото напрямую на устройство через ISAPI с несколькими методами fallback.
    
    Args:
        device: HikDevice object
        person_code: Код персоны (обычно guest_id)
        image_bytes: Байты изображения
        
    Returns:
        True если успешно, False если ошибка
    """
    from requests.auth import HTTPDigestAuth
    import io
    
    logger.info(f"ISAPI: Uploading face for person {person_code} to device {device.name} ({device.host})")
    
    try:
        auth = HTTPDigestAuth(device.username, device.password)
        
        # Метод 1: Multipart PUT с бинарным изображением
        try:
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            
            multipart_data = MultipartEncoder(
                fields={
                    'FaceDataRecord': (
                        'face.jpg',
                        io.BytesIO(image_bytes),
                        'image/jpeg'
                    )
                }
            )
            
            url = f"http://{device.host}/ISAPI/Intelligent/FDLib/FaceDataRecord/picture?FDID=1&faceID={person_code}"
            response = requests.put(
                url,
                data=multipart_data,
                auth=auth,
                headers={'Content-Type': multipart_data.content_type},
                timeout=30
            )
            
            logger.info(f"ISAPI: Method 1 (PUT multipart) response: {response.status_code}")
            if response.status_code in [200, 201]:
                logger.info(f"ISAPI: Successfully uploaded face for {person_code} to {device.name} via PUT multipart")
                return True
            else:
                logger.warning(f"ISAPI: Method 1 failed with {response.status_code}")
                logger.warning(f"ISAPI: Full response: {response.text}")
        except Exception as e:
            logger.warning(f"ISAPI: Method 1 (PUT multipart) failed: {e}")
        
        # Метод 2: POST XML с base64 в теге <faceData>
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            xml_payload = f'''<?xml version="1.0" encoding="UTF-8"?>
<FaceDataRecord>
    <faceLibType>blackFD</faceLibType>
    <FDID>1</FDID>
    <faceID>{person_code}</faceID>
    <faceData>{image_base64}</faceData>
</FaceDataRecord>'''
            
            url = f"http://{device.host}/ISAPI/Intelligent/FDLib/FaceDataRecord"
            response = requests.post(
                url,
                data=xml_payload.encode('utf-8'),
                auth=auth,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            
            logger.info(f"ISAPI: Method 2 (POST XML faceData) response: {response.status_code}")
            if response.status_code in [200, 201]:
                logger.info(f"ISAPI: Successfully uploaded face for {person_code} to {device.name} via POST XML")
                return True
            else:
                logger.warning(f"ISAPI: Method 2 failed with {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"ISAPI: Method 2 (POST XML) failed: {e}")
        
        # Метод 3: Binary POST к FDSetUp/picture
        try:
            url = f"http://{device.host}/ISAPI/Intelligent/FDLib/FDSetUp/picture?FDID=1"
            response = requests.post(
                url,
                data=image_bytes,
                auth=auth,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=30
            )
            
            logger.info(f"ISAPI: Method 3 (Binary POST) response: {response.status_code}")
            if response.status_code in [200, 201]:
                logger.info(f"ISAPI: Successfully uploaded face for {person_code} to {device.name} via Binary POST")
                return True
            else:
                logger.warning(f"ISAPI: Method 3 failed with {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"ISAPI: Method 3 (Binary POST) failed: {e}")
        
        # Все методы провалились
        logger.error(f"ISAPI: All upload methods failed for {device.name}")
        return False
        
    except Exception as e:
        logger.error(f"ISAPI: Critical error uploading to {device.name}: {e}")
        return False
            
    except requests.exceptions.Timeout:
        logger.error(f"ISAPI: Timeout uploading to {device.name}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"ISAPI: Connection error to {device.name}")
        return False
    except Exception as e:
        logger.error(f"ISAPI: Unexpected error uploading to {device.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


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


def visitor_registerment(session: HikCentralSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Создать/зарегистрировать визитёра: POST /artemis/api/visitor/v1/registerment"""
    try:
        resp = session._make_request('POST', '/artemis/api/visitor/v1/registerment', data=payload)
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("visitor_registerment failed: %s", e)
        raise


def visitor_update(session: HikCentralSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Изменить визит: POST /artemis/api/visitor/v1/registerment/update"""
    try:
        resp = session._make_request('POST', '/artemis/api/visitor/v1/registerment/update', data=payload)
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("visitor_update failed: %s", e)
        raise


def visitor_out(session: HikCentralSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Отметить выход визитёра: POST /artemis/api/visitor/v1/visitor/out
    Ожидается минимум { 'personId': '...' } или другой идентификатор согласно конфигурации HCP.
    """
    try:
        resp = session._make_request('POST', '/artemis/api/visitor/v1/visitor/out', data=payload)
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("visitor_out failed: %s", e)
        raise


def visitor_auth_reapplication(session: HikCentralSession, person_id: str) -> Dict[str, Any]:
    """Триггер применения настроек на устройства: POST /artemis/api/visitor/v1/auth/reapplication"""
    try:
        resp = session._make_request('POST', '/artemis/api/visitor/v1/auth/reapplication', data={'personId': str(person_id)})
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("visitor_auth_reapplication failed: %s", e)
        raise


def visitor_auth_result(
    session: HikCentralSession,
    person_id: str,
    result_type: int = 2,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Статус применения прав: POST /artemis/api/acs/v1/auth/applicationResult"""
    from datetime import datetime, timedelta
    if not start_time or not end_time:
        now = datetime.now()
        start_time = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
        end_time = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
    payload = {
        'pageNo': 1,
        'pageSize': 10,
        'type': result_type,
        'applicationResultType': result_type,
        'startTime': start_time,
        'endTime': end_time,
        'personId': str(person_id),
    }
    try:
        resp = session._make_request('POST', '/artemis/api/acs/v1/auth/applicationResult', data=payload)
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("visitor_auth_result failed: %s", e)
        raise


def assign_access_level_to_person(
    session: HikCentralSession,
    person_id: str,
    access_group_id: str,
    access_type: int = 1
) -> bool:
    """
    Назначает гостю access level group.
    
    Args:
        session: HikCentral session
        person_id: ID Person в HCP
        access_group_id: ID группы доступа (privilegeGroupId)
        access_type: 1=access control, 2=visitor
        
    Returns:
        True если успешно, False если ошибка
    """
    logger.info(
        "HikCentral: Assigning access level group %s to person %s (type=%d)",
        access_group_id, person_id, access_type
    )
    
    try:
        # Назначаем access level через addPersons API
        payload = {
            'privilegeGroupId': str(access_group_id),
            'type': access_type,
            'list': [
                {'id': str(person_id)}
            ]
        }
        
        resp = session._make_request(
            'POST',
            '/artemis/api/acs/v1/privilege/group/single/addPersons',
            data=payload
        )
        
        result = resp.json()
        logger.info(
            "HikCentral: addPersons response code=%s msg=%s",
            result.get('code'), result.get('msg')
        )
        
        if result.get('code') != '0':
            logger.error(
                "HikCentral: Failed to assign access level: %s",
                result.get('msg')
            )
            return False
        
        # Применяем изменения на устройства через reapplication
        logger.info("HikCentral: Applying access settings to devices...")
        
        reapply_payload = {
            'personIds': str(person_id),
            'ImmediateDownload': 1  # Немедленно применить
        }
        
        reapply_resp = session._make_request(
            'POST',
            '/artemis/api/visitor/v1/auth/reapplication',
            data=reapply_payload
        )
        
        reapply_result = reapply_resp.json()
        logger.info(
            "HikCentral: reapplication response code=%s msg=%s",
            reapply_result.get('code'), reapply_result.get('msg')
        )
        
        if reapply_result.get('code') != '0':
            logger.warning(
                "HikCentral: Reapplication warning: %s",
                reapply_result.get('msg')
            )
            # Не считаем это критичной ошибкой - группа назначена
        
        logger.info(
            "HikCentral: Successfully assigned access level to person %s",
            person_id
        )
        return True
        
    except Exception as e:
        logger.error(
            "HikCentral: Failed to assign access level to person %s: %s",
            person_id, e
        )
        import traceback
        traceback.print_exc()
        return False


def revoke_access_level_from_person(
    session: HikCentralSession,
    person_id: str,
    access_group_id: str,
    access_type: int = 1
) -> bool:
    """
    Отзывает access level у гостя.
    
    Args:
        session: HikCentral session
        person_id: ID Person в HCP
        access_group_id: ID группы доступа (privilegeGroupId)
        access_type: 1=access control, 2=visitor
        
    Returns:
        True если успешно, False если ошибка
    """
    logger.info(
        "HikCentral: Revoking access level group %s from person %s (type=%d)",
        access_group_id, person_id, access_type
    )
    
    try:
        # Отзываем access level через deletePersons API
        payload = {
            'privilegeGroupId': str(access_group_id),
            'type': access_type,
            'list': [
                {'id': str(person_id)}
            ]
        }
        
        resp = session._make_request(
            'POST',
            '/artemis/api/acs/v1/privilege/group/single/deletePersons',
            data=payload
        )
        
        result = resp.json()
        logger.info(
            "HikCentral: deletePersons response code=%s msg=%s",
            result.get('code'), result.get('msg')
        )
        
        if result.get('code') != '0':
            logger.error(
                "HikCentral: Failed to revoke access level: %s",
                result.get('msg')
            )
            return False
        
        # Применяем изменения на устройства
        logger.info("HikCentral: Applying revocation to devices...")
        
        reapply_payload = {
            'personIds': str(person_id),
            'ImmediateDownload': 1
        }
        
        reapply_resp = session._make_request(
            'POST',
            '/artemis/api/visitor/v1/auth/reapplication',
            data=reapply_payload
        )
        
        reapply_result = reapply_resp.json()
        logger.info(
            "HikCentral: reapplication response code=%s msg=%s",
            reapply_result.get('code'), reapply_result.get('msg')
        )
        
        logger.info(
            "HikCentral: Successfully revoked access level from person %s",
            person_id
        )
        return True
        
    except Exception as e:
        logger.error(
            "HikCentral: Failed to revoke access level from person %s: %s",
            person_id, e
        )
        import traceback
        traceback.print_exc()
        return False


def get_door_events(
    session: HikCentralSession,
    person_id: str = None,
    person_name: str = None,
    start_time: str = None,
    end_time: str = None,
    door_index_codes: list[str] = None,
    event_type: int = None,
    page_no: int = 1,
    page_size: int = 100
) -> dict:
    """
    Получает события прохода через турникеты/двери.
    
    Args:
        session: HikCentral session
        person_id: ID Person (опционально)
        person_name: Имя человека (опционально)
        start_time: Начало периода (ISO 8601: yyyy-MM-ddTHH:mm:ss+TZ)
        end_time: Конец периода (ISO 8601: yyyy-MM-ddTHH:mm:ss+TZ)
        door_index_codes: Список ID дверей (опционально)
        event_type: Тип события (опционально, например 197151)
        page_no: Номер страницы
        page_size: Размер страницы
        
    Returns:
        Dict с результатами или пустой dict при ошибке
    """
    from datetime import datetime, timedelta, timezone as tz
    
    # Если время не указано - берем последние 24 часа
    if not start_time or not end_time:
        now = datetime.now(tz.utc)
        start_time = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        end_time = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    
    payload = {
        'startTime': start_time,
        'endTime': end_time,
        'pageNo': page_no,
        'pageSize': page_size,
        'doorIndexCodes': door_index_codes or [],
    }
    
    # По документации - нужен либо eventType либо personName
    if event_type:
        payload['eventType'] = event_type
    elif person_name:
        payload['personName'] = person_name
    else:
        # Если ничего не указано - используем событие "successful entry"
        payload['eventType'] = 197151
    
    logger.info(
        "HikCentral: Getting door events for person %s/%s from %s to %s",
        person_id, person_name, start_time, end_time
    )
    
    try:
        resp = session._make_request(
            'POST',
            '/artemis/api/acs/v1/door/events',
            data=payload
        )
        
        result = resp.json()
        
        if result.get('code') != '0':
            logger.warning(
                "HikCentral: door/events returned code=%s msg=%s",
                result.get('code'), result.get('msg')
            )
            return {}
        
        events = result.get('data', {}).get('list', [])
        logger.info(
            "HikCentral: Found %d door events",
            len(events)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "HikCentral: Failed to get door events: %s",
            e
        )
        import traceback
        traceback.print_exc()
        return {}


