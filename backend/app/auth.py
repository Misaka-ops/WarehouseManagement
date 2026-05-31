from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings


security_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str = "admin"
    expires_at: datetime | None = None


def authenticate_admin(username: str, password: str) -> AuthUser | None:
    settings = get_settings()
    normalized_username = username.strip()

    if not compare_digest(normalized_username, settings.auth_admin_username):
        return None
    if not compare_digest(password, settings.auth_admin_password):
        return None
    return AuthUser(username=normalized_username)


def create_access_token(user: AuthUser) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=max(settings.auth_token_ttl_hours, 1))
    payload = {
        "sub": user.username,
        "role": user.role,
        "exp": int(expires_at.timestamp()),
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = _sign_payload(body)
    token = f"{_urlsafe_b64encode(body)}.{_urlsafe_b64encode(signature)}"
    return token, expires_at


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthUser | None:
    if credentials is None:
        return None
    try:
        return _resolve_user_from_credentials(credentials)
    except HTTPException:
        return None


def require_authenticated_user(user: AuthUser | None = Depends(get_optional_current_user)) -> AuthUser:
    if user is None:
        raise _unauthorized("请先登录。")
    return user


def resolve_session(
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[AuthUser | None, datetime | None]:
    if credentials is None:
        return None, None
    try:
        user = _resolve_user_from_credentials(credentials)
    except HTTPException:
        return None, None
    return user, user.expires_at


def _resolve_user_from_credentials(credentials: HTTPAuthorizationCredentials) -> AuthUser:
    if credentials.scheme.lower() != "bearer":
        raise _unauthorized("登录凭证格式不正确。")
    return decode_access_token(credentials.credentials)


def decode_access_token(token: str) -> AuthUser:
    settings = get_settings()
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise _unauthorized("登录凭证无效，请重新登录。") from exc

    payload_bytes = _urlsafe_b64decode(payload_part)
    provided_signature = _urlsafe_b64decode(signature_part)
    expected_signature = _sign_payload(payload_bytes)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise _unauthorized("登录凭证校验失败，请重新登录。")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _unauthorized("登录凭证无效，请重新登录。") from exc

    username = str(payload.get("sub") or "").strip()
    role = str(payload.get("role") or "admin").strip() or "admin"
    expires_unix = int(payload.get("exp") or 0)
    if not username or role != "admin":
        raise _unauthorized("登录凭证无效，请重新登录。")

    current_unix = int(time.time())
    if expires_unix <= current_unix:
        raise _unauthorized("登录已过期，请重新登录。")

    if username != settings.auth_admin_username:
        raise _unauthorized("当前账号已失效，请重新登录。")

    expires_at = datetime.fromtimestamp(expires_unix, tz=timezone.utc)
    return AuthUser(username=username, role=role, expires_at=expires_at)


def _sign_payload(payload: bytes) -> bytes:
    secret = get_settings().auth_token_secret.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).digest()


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8"))
    except (ValueError, binascii.Error) as exc:
        raise _unauthorized("登录凭证无效，请重新登录。") from exc


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
