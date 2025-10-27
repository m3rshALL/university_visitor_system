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


logger = logging.getLogger(__name__)


def escape_xml(text: str) -> str:
    """
    Экранирует спецсимволы XML для предотвращения XML injection.
    
    Args:
        text: Строка для экранирования
        
    Returns:
        Безопасная строка для использования в XML
        
    Example:
        >>> escape_xml("O'Reilly & Associates")
        "O&apos;Reilly &amp; Associates"
    """
    if not text:
        return ''
    import xml.sax.saxutils as saxutils
    return saxutils.escape(str(text))


class HikCentralSession:
    """Сессия для работы с HikCentral Professional OpenAPI (AK/SK подпись Artemis)."""

    def __init__(self, server: HikCentralServer):
        self.server = server
        self.base_url = server.base_url.rstrip('/')
        self.session = requests.Session()
        ca_bundle = getattr(settings, 'HIKCENTRAL_CA_BUNDLE', '').strip()
        verify_tls = getattr(settings, 'HIKCENTRAL_VERIFY_TLS', not settings.DEBUG)
        if ca_bundle:
            self.session.verify = ca_bundle
        else:
            self.session.verify = verify_tls
        if not self.session.verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning(
                'HikCentralSession for %s started with TLS verification disabled',
                server.name
            )
        
        # Настройка connection pool для оптимальной производительности
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=50,  # Количество connection pools
            pool_maxsize=50,      # Максимальный размер каждого pool
            max_retries=3,        # Автоматические retry для сетевых ошибок
            pool_block=False      # Не блокировать при исчерпании pool
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        logger.info(f"HikCentralSession initialized for {server.name}")
    
    def __enter__(self):
        """Context manager entry - возвращает self для использования в with statement."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - автоматически закрывает сессию для предотвращения memory leak."""
        if self.session:
            self.session.close()
            logger.debug(f"HikCentralSession closed for {self.server.name}")
        return False  # Не подавляем exceptions

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
        # Rate limiting для предотвращения перегрузки HCP сервера
        from .rate_limiter import get_rate_limiter
        rate_limiter = get_rate_limiter()
        rate_limiter.acquire()
        
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

        max_retries_429 = 3
        for retry_attempt in range(max_retries_429):
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

            except requests.exceptions.HTTPError as e:
                # Специальная обработка HTTP 429 (Rate Limit Exceeded)
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    if retry_attempt < max_retries_429 - 1:
                        logger.warning(
                            "HCP rate limit exceeded (429), retry after %d seconds (attempt %d/%d)",
                            retry_after, retry_attempt + 1, max_retries_429
                        )
                        import time
                        time.sleep(retry_after)
                        continue  # Retry
                    else:
                        logger.error("HCP rate limit exceeded, max retries reached")
                        raise
                else:
                    # Другие HTTP ошибки - не retry
                    logger.error(f"HikCentral HTTP error {e.response.status_code}: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"HikCentral API request failed: {e}")
                raise

    def get(self, endpoint: str, params: Dict = None) -> requests.Response:
        """GET request with AK/SK signature."""
        return self._make_request('GET', endpoint, data=None, params=params)

    def post(
        self, endpoint: str, json: Dict = None, params: Dict = None
    ) -> requests.Response:
        """POST request with AK/SK signature."""
        return self._make_request('POST', endpoint, data=json, params=params)

    def put(
        self, endpoint: str, json: Dict = None, params: Dict = None
    ) -> requests.Response:
        """PUT request with AK/SK signature."""
        return self._make_request('PUT', endpoint, data=json, params=params)


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


# ============================================================================
# DEPRECATED: Old ISAPI Methods (Legacy)
# Эти методы устарели и используются только для совместимости со старыми
# устройствами без HikCentral Professional.
# Для современных систем используйте HikCentral OpenAPI методы:
# - ensure_person_hikcentral() вместо ensure_person()
# - upload_face_hikcentral() вместо upload_face()
# - assign_access_hikcentral() вместо assign_access()
# - revoke_access_hikcentral() вместо revoke_access()
# ============================================================================


def ensure_person(session: HikSession, employee_no: str, name: str,
                  valid_from: Optional[str], valid_to: Optional[str]) -> str:
    """DEPRECATED: Старый метод ISAPI. Используйте ensure_person_hikcentral().

    Создает или обновляет пользователя в системе Hikvision через ISAPI.
    Используется только для устройств без HikCentral Professional.
    """
    logger.warning(
        "DEPRECATED: Using legacy ISAPI method ensure_person(). "
        "Consider upgrading to HikCentral Professional."
    )
    logger.info(f"Hikvision: Ensuring person {name} ({employee_no}) via ISAPI")

    # Формируем XML для создания/обновления пользователя (с защитой от XML injection)
    person_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<UserInfo>
    <employeeNo>{escape_xml(employee_no)}</employeeNo>
    <name>{escape_xml(name)}</name>
    <userType>normal</userType>
    <localRight>1</localRight>
    <maxOpenDoorTime>0</maxOpenDoorTime>
    <Valid>
        <enable>true</enable>
        <beginTime>{escape_xml(valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))}</beginTime>
        <endTime>{escape_xml(valid_to or (datetime.now().replace(
            year=datetime.now().year + 1
        )).strftime('%Y-%m-%dT%H:%M:%S'))}</endTime>
    </Valid>
</UserInfo>"""

    try:
        # Проверяем, существует ли пользователь
        check_response = session.get(
            f'/ISAPI/AccessControl/UserInfo/{employee_no}'
        )

        if check_response.status_code == 200:
            # Пользователь существует, обновляем
            response = session.put(
                f'/ISAPI/AccessControl/UserInfo/{employee_no}',
                data=person_xml
            )
            logger.info(f"Hikvision: Updated existing person {employee_no}")
        else:
            # Пользователь не существует, создаем
            response = session.post(
                '/ISAPI/AccessControl/UserInfo',
                data=person_xml
            )
            logger.info(f"Hikvision: Created new person {employee_no}")

        return employee_no

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to ensure person {employee_no}: {e}")
        # Возвращаем employee_no как person_id даже при ошибке
        return employee_no


def upload_face(session: HikSession, face_lib_id: str,
                image_bytes: bytes, person_id: str) -> str:
    """DEPRECATED: Старый метод ISAPI. Используйте upload_face_hikcentral().

    Загружает фото лица в библиотеку лиц Hikvision через ISAPI.
    Используется только для устройств без HikCentral Professional.

    Сначала пытается загрузить фото напрямую к персоне через
    /ISAPI/Intelligent/FDLib/picture, затем пробует старый метод через
    FaceDataRecord если первый не сработал.
    """
    logger.warning(
        "DEPRECATED: Using legacy ISAPI method upload_face(). "
        "Consider upgrading to HikCentral Professional."
    )
    logger.info(
        f"Hikvision ISAPI: Uploading face for person {person_id} "
        f"to library {face_lib_id}"
    )

    try:
        # Метод 1: POST с base64 через XML
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # XML payload для FaceDataRecord (с защитой от XML injection)
        face_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FaceDataRecord>
    <faceLibType>blackFD</faceLibType>
    <FDID>{escape_xml(face_lib_id)}</FDID>
    <faceID>{escape_xml(person_id)}</faceID>
    <faceData>{image_base64}</faceData>
</FaceDataRecord>"""

        response = session.post(
            '/ISAPI/Intelligent/FDLib/FaceDataRecord', data=face_xml
        )

        if response.status_code in [200, 201]:
            logger.info(
                f"Hikvision ISAPI: Successfully uploaded face via "
                f"POST XML for person {person_id}"
            )
            return f"face_{person_id}"
        else:
            logger.warning(
                f"Hikvision ISAPI: Face upload XML returned status "
                f"{response.status_code}"
            )
            # Пробуем альтернативный endpoint
            response_alt = session.post(
                f'/ISAPI/Intelligent/FDLib/FDSetUp/picture?'
                f'format=json&FDID={face_lib_id}',
                data=image_bytes,
                headers={'Content-Type': 'application/octet-stream'}
            )
            if response_alt.status_code in [200, 201]:
                logger.info(
                    f"Hikvision ISAPI: Successfully uploaded via "
                    f"FDSetUp/picture for person {person_id}"
                )
                return f"face_{person_id}"

            return f"face_{person_id}_status_{response.status_code}"

    except Exception as e:
        logger.error(
            f"Hikvision ISAPI: Failed to upload face for person "
            f"{person_id}: {e}"
        )
        return f"face_{person_id}_error"


def assign_access(session: HikSession, person_id: str, door_ids: List[str],
                  valid_from: Optional[str], valid_to: Optional[str]) -> None:
    """DEPRECATED: Старый метод ISAPI. Используйте assign_access_hikcentral().

    Назначает доступ к дверям для пользователя через ISAPI.
    Используется только для устройств без HikCentral Professional.
    """
    logger.warning(
        "DEPRECATED: Using legacy ISAPI method assign_access(). "
        "Consider upgrading to HikCentral Professional."
    )
    logger.info(
        f"Hikvision: Assigning access for person {person_id} "
        f"to doors {door_ids}"
    )

    try:
        for door_id in door_ids:
            # Формируем XML для назначения прав доступа
            begin_time = (
                valid_from or datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            )
            end_time = (
                valid_to or (datetime.now().replace(
                    year=datetime.now().year + 1
                )).strftime('%Y-%m-%dT%H:%M:%S')
            )
            # Формируем XML с защитой от XML injection
            access_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<DoorRight>
    <employeeNo>{escape_xml(person_id)}</employeeNo>
    <doorNo>{escape_xml(door_id)}</doorNo>
    <planTemplateNo>1</planTemplateNo>
    <valid>
        <enable>true</enable>
        <beginTime>{escape_xml(begin_time)}</beginTime>
        <endTime>{escape_xml(end_time)}</endTime>
    </valid>
</DoorRight>"""

            response = session.post(
                '/ISAPI/AccessControl/DoorRight', data=access_xml
            )

            if response.status_code in [200, 201]:
                logger.info(
                    f"Hikvision: Successfully assigned access for person "
                    f"{person_id} to door {door_id}"
                )
            else:
                logger.warning(
                    f"Hikvision: Access assignment returned status "
                    f"{response.status_code} for door {door_id}"
                )

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to assign access for person {person_id}: {e}")


def revoke_access(session: HikSession, person_id: str,
                  door_ids: List[str]) -> None:
    """DEPRECATED: Старый метод ISAPI. Используйте revoke_access_hikcentral().

    Отзывает доступ к дверям для пользователя через ISAPI.
    Используется только для устройств без HikCentral Professional.
    """
    logger.warning(
        "DEPRECATED: Using legacy ISAPI method revoke_access(). "
        "Consider upgrading to HikCentral Professional."
    )
    logger.info(
        f"Hikvision: Revoking access for person {person_id} "
        f"from doors {door_ids}"
    )

    try:
        for door_id in door_ids:
            # Удаляем права доступа
            response = session._make_request(
                'DELETE',
                f'/ISAPI/AccessControl/DoorRight/{person_id}/{door_id}'
            )

            if response.status_code in [200, 204]:
                logger.info(
                    f"Hikvision: Successfully revoked access for person "
                    f"{person_id} from door {door_id}"
                )
            else:
                logger.warning(
                    f"Hikvision: Access revocation returned status "
                    f"{response.status_code} for door {door_id}"
                )

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to revoke access for person {person_id}: {e}")


# ============================================================================
# End of DEPRECATED ISAPI Methods
# ============================================================================


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
        
    except Exception:
        logger.exception("HikCentral: Failed to upload face with validation")
        return False


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
        
        logger.info("HikCentral: Sending payload with personId=%s, faceData length=%d chars",
                   person_id, len(image_base64))
        
        # РАБОЧИЙ endpoint: /person/face/update!
        face_resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=update_payload)
        face_json = face_resp.json()
        
        logger.info("HikCentral: person/face/update response code=%s msg=%s",
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
    except Exception:
        logger.exception("HikCentral: Unexpected error uploading face for %s", person_id)
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
    
    logger.info(f"ISAPI: Uploading face for person {person_code} to device {device.name} ({device.host})")
    
    try:
        auth = HTTPDigestAuth(device.username, device.password)
        
        # Метод 1: POST XML с base64 в теге <faceData>
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # XML с защитой от injection
            xml_payload = f'''<?xml version="1.0" encoding="UTF-8"?>
<FaceDataRecord>
    <faceLibType>blackFD</faceLibType>
    <FDID>1</FDID>
    <faceID>{escape_xml(person_code)}</faceID>
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
            
            logger.info(f"ISAPI: Method 1 (POST XML faceData) response: {response.status_code}")
            if response.status_code in [200, 201]:
                logger.info(f"ISAPI: Successfully uploaded face for {person_code} to {device.name} via POST XML")
                return True
            else:
                logger.warning(f"ISAPI: Method 1 failed with {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"ISAPI: Method 1 (POST XML) failed: {e}")
        
        # Метод 2: Binary POST к FDSetUp/picture
        try:
            url = f"http://{device.host}/ISAPI/Intelligent/FDLib/FDSetUp/picture?FDID=1"
            response = requests.post(
                url,
                data=image_bytes,
                auth=auth,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=30
            )
            
            logger.info(f"ISAPI: Method 2 (Binary POST) response: {response.status_code}")
            if response.status_code in [200, 201]:
                logger.info(f"ISAPI: Successfully uploaded face for {person_code} to {device.name} via Binary POST")
                return True
            else:
                logger.warning(f"ISAPI: Method 2 failed with {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"ISAPI: Method 2 (Binary POST) failed: {e}")
        
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
    except Exception:
        logger.exception("ISAPI: Unexpected error uploading to %s", device.name)
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
        
    except Exception:
        logger.exception(
            "HikCentral: Failed to assign access level to person %s",
            person_id
        )
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
        
    except Exception:
        logger.exception(
            "HikCentral: Failed to revoke access level from person %s",
            person_id
        )
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
        
    except Exception:
        logger.exception("HikCentral: Failed to get door events")
        return {}


def get_person_hikcentral(session, person_id: str) -> dict:
    """
    FIX #10: Получает информацию о персоне из HikCentral.
    
    Args:
        session: HikCentralSession объект
        person_id: ID персоны в HikCentral
    
    Returns:
        dict: Данные персоны если найдена, иначе {}
        Содержит поля: personId, personName, startTime, endTime, status, и т.д.
    
    Example response:
        {
            "personId": "8512",
            "personName": "Guest Name",
            "startTime": "2025-10-03T09:00:00+00:00",
            "endTime": "2025-10-03T22:00:00+00:00",
            "status": 1,  # 1=active, 0=inactive
            ...
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Используем POST /person/personId/personInfo для получения данных персоны
        payload = {'personId': str(person_id)}
        
        resp = session.post(
            '/artemis/api/resource/v1/person/personId/personInfo',
            json=payload
        )
        
        if resp.status_code != 200:
            logger.error(
                "HikCentral: Failed to get person %s: status=%d",
                person_id, resp.status_code
            )
            return {}
        
        result = resp.json()
        if result.get('code') != '0':
            logger.warning(
                "HikCentral: Person %s not found or error: code=%s, msg=%s",
                person_id, result.get('code'), result.get('msg')
            )
            return {}
        
        # Ответ содержит данные персоны напрямую в поле 'data'
        data = result.get('data', {})
        
        if not data or not data.get('personId'):
            logger.warning("HikCentral: Person %s not found in results", person_id)
            return {}
        
        logger.info(
            "HikCentral: Found person %s (status=%s, endTime=%s)",
            person_id,
            data.get('status'),
            data.get('endTime')
        )
        
        return data
        
    except Exception:
        logger.exception(
            "HikCentral: Failed to get person %s",
            person_id
        )
        return {}
