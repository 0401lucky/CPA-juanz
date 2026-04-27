import base64
import hashlib
import hmac
import secrets
from typing import Any

from itsdangerous import BadSignature, URLSafeSerializer


def generate_management_code() -> str:
    return secrets.token_urlsafe(18)


def hash_management_code(management_code: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", management_code.encode("utf-8"), salt, 210_000
    )
    return (
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8")
    )


def verify_management_code(management_code: str, salt_b64: str, digest_b64: str) -> bool:
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    expected = base64.b64decode(digest_b64.encode("utf-8"))
    actual = hashlib.pbkdf2_hmac(
        "sha256", management_code.encode("utf-8"), salt, 210_000
    )
    return hmac.compare_digest(actual, expected)


class SessionManager:
    def __init__(self, secret_key: str) -> None:
        self._serializer = URLSafeSerializer(secret_key=secret_key)

    def sign_donor_session(self, donor_id: str) -> str:
        return self._serializer.dumps({"role": "donor", "donor_id": donor_id})

    def load_donor_session(self, token: str | None) -> str | None:
        if not token:
            return None
        try:
            payload: dict[str, Any] = self._serializer.loads(token)
        except BadSignature:
            return None
        if payload.get("role") != "donor":
            return None
        donor_id = payload.get("donor_id")
        if not isinstance(donor_id, str) or not donor_id:
            return None
        return donor_id

    def sign_admin_session(self) -> str:
        return self._serializer.dumps({"role": "admin"})

    def is_admin_session(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            payload: dict[str, Any] = self._serializer.loads(token)
        except BadSignature:
            return False
        return payload.get("role") == "admin"

