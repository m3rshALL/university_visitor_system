import base64
import logging
from typing import Any, Dict, List, Optional
import requests


logger = logging.getLogger(__name__)


class HikSession:
    def __init__(self, host: str, port: int, username: str, password: str, verify_ssl: bool = False):
        self.base = f"http://{host}:{port}"
        self.auth = (username, password)
        self.verify = verify_ssl

    def get(self, path: str, **kw) -> requests.Response:
        url = self.base + path
        return requests.get(url, auth=self.auth, verify=self.verify, timeout=kw.get('timeout', 10))

    def post(self, path: str, **kw) -> requests.Response:
        url = self.base + path
        return requests.post(url, auth=self.auth, verify=self.verify, timeout=kw.get('timeout', 15), **kw)

    def put(self, path: str, **kw) -> requests.Response:
        url = self.base + path
        return requests.put(url, auth=self.auth, verify=self.verify, timeout=kw.get('timeout', 15), **kw)


def ensure_person(session: HikSession, employee_no: str, name: str, valid_from: Optional[str], valid_to: Optional[str]) -> str:
    """Создать/обновить пользователя на контроллере. Возвращает person_id (employee_no)."""
    # Заглушка: считаем, что employee_no = person_id
    logger.info("ensure_person %s %s", employee_no, name)
    return employee_no


def upload_face(session: HikSession, face_lib_id: str, image_bytes: bytes, person_id: str) -> str:
    """Загрузить лицо в библиотеку и связать с человеком. Возвращает face_id."""
    logger.info("upload_face %s len=%s", person_id, len(image_bytes))
    return person_id + ":face"


def assign_access(session: HikSession, person_id: str, door_ids: List[str], valid_from: Optional[str], valid_to: Optional[str]) -> None:
    logger.info("assign_access %s doors=%s", person_id, door_ids)


def revoke_access(session: HikSession, person_id: str, door_ids: List[str]) -> None:
    logger.info("revoke_access %s doors=%s", person_id, door_ids)


