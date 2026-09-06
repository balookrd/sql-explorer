import uuid
import datetime
import ipaddress
from typing import Optional, List
from pydantic import BaseModel
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)

TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost", "testclient"}

def is_trusted_proxy(host: str) -> bool:
    if host in TRUSTED_PROXIES:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        return False

def get_client_ip(request: Request) -> str:
    """
    Безопасное определение IP-адреса клиента с защитой от IP Spoofing (CWE-348 / CWE-290).
    X-Forwarded-For считывается только если непосредственный request.client.host является доверенным прокси.
    """
    if not request.client or not request.client.host:
        return "unknown"
    
    direct_ip = request.client.host
    if is_trusted_proxy(direct_ip):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
            if ips:
                return ips[0]
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
            
    return direct_ip

from urllib.parse import urlparse

def _is_allowed_origin(url_str: str, request: Request, allowed_cors: list[str]) -> bool:
    if not url_str:
        return False
    try:
        parsed = urlparse(url_str)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.scheme.lower() not in ("http", "https"):
            return False

        target_origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}".rstrip("/")
        target_netloc = parsed.netloc.lower()

        for allowed in allowed_cors:
            if allowed == "*":
                return True
            p_allowed = urlparse(allowed)
            if p_allowed.netloc:
                if f"{p_allowed.scheme.lower()}://{p_allowed.netloc.lower()}".rstrip("/") == target_origin:
                    return True
            elif allowed.rstrip("/").lower() == target_origin:
                return True

        req_host = request.headers.get("host", "").lower()
        if req_host and target_netloc == req_host:
            return True

        base_netloc = request.base_url.netloc.lower()
        if base_netloc and target_netloc == base_netloc:
            return True

        base_url_str = str(request.base_url).rstrip("/").lower()
        if target_origin == base_url_str:
            return True

        return False
    except Exception:
        return False

def verify_csrf(request: Request, is_cookie_auth: bool):
    """
    Защита от Cross-Site Request Forgery (CWE-352).
    Если запрос аутентифицирован через Cookie и изменяет состояние (POST, PUT, DELETE, PATCH),
    требуется подтверждение легитимности источника (Sec-Fetch-Site, Origin, Referer, X-Requested-With).
    """
    if not is_cookie_auth:
        return

    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        sec_fetch_site = request.headers.get("Sec-Fetch-Site")
        if sec_fetch_site and sec_fetch_site.lower() == "cross-site":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF protection: межсайтовый запрос отклонен (Sec-Fetch-Site: cross-site)"
            )

        x_requested_with = request.headers.get("X-Requested-With")
        if x_requested_with == "XMLHttpRequest":
            return

        origin = request.headers.get("Origin")
        if origin and _is_allowed_origin(origin, request, settings.server.cors_origins):
            return

        referer = request.headers.get("Referer")
        if referer and _is_allowed_origin(referer, request, settings.server.cors_origins):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF protection: запрос отклонен политикой безопасности источника"
        )

class UserSession(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    groups: List[str] = []
    is_admin: bool = False
    auth_method: str = "ldap"  # ldap, kerberos, mock

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + datetime.timedelta(minutes=settings.auth.jwt.expire_minutes)
    to_encode.update({
        "exp": expire,
        "iat": now_utc,
        "jti": uuid.uuid4().hex
    })
    encoded_jwt = jwt.encode(to_encode, settings.auth.jwt.secret_key, algorithm=settings.auth.jwt.algorithm)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.auth.jwt.secret_key, algorithms=[settings.auth.jwt.algorithm])
        return payload
    except jwt.PyJWTError:
        return None

import hashlib
from sqlalchemy import select, delete
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.models import RevokedToken

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# L1 In-memory кэш отозванных токенов для мгновенной проверки (с ограничением размера)
_revoked_tokens_cache: set[str] = set()
_MAX_REVOKED_CACHE_SIZE = 10000

def _add_to_revoked_cache(h: str):
    if len(_revoked_tokens_cache) >= _MAX_REVOKED_CACHE_SIZE:
        _revoked_tokens_cache.clear()
    _revoked_tokens_cache.add(h)

async def revoke_token_in_db(
    token: str,
    username: str = "unknown",
    expires_at: Optional[datetime.datetime] = None
):
    """
    Отзывает JWT токен и сохраняет его хэш в персистентную БД (SQLite/PostgreSQL)
    с автоматической очисткой устаревших записей.
    """
    h = hash_token(token)
    _add_to_revoked_cache(h)

    if not expires_at:
        payload = decode_access_token(token)
        if payload and "exp" in payload:
            expires_at = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
        else:
            expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.auth.jwt.expire_minutes)

    now = datetime.datetime.now(datetime.timezone.utc)
    async with AsyncSessionLocal() as db:
        record = RevokedToken(
            token_hash=h,
            username=username,
            expires_at=expires_at,
            revoked_at=now
        )
        db.add(record)
        # Очищаем из БД старые токены, срок действия которых уже истек
        await db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
        await db.commit()

async def is_token_revoked_in_db(token: str) -> bool:
    """
    Проверяет, отозван ли токен, сначала в L1 кэше, затем в БД (SQLite/PostgreSQL).
    """
    h = hash_token(token)
    if h in _revoked_tokens_cache:
        return True

    now = datetime.datetime.now(datetime.timezone.utc)
    async with AsyncSessionLocal() as db:
        stmt = select(RevokedToken.token_hash).where(
            RevokedToken.token_hash == h,
            RevokedToken.expires_at >= now
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            _add_to_revoked_cache(h)
            return True
        return False

def revoke_token(token: str):
    """Синхронная обертка для обратной совместимости"""
    _add_to_revoked_cache(hash_token(token))

def is_token_revoked(token: str) -> bool:
    """Синхронная проверка по L1 кэшу"""
    return hash_token(token) in _revoked_tokens_cache

class LoginRateLimiter:
    """
    Лимитер количества попыток аутентификации для защиты от Brute-force и Password Spraying (CWE-307 / CWE-400).
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60, max_tracked_keys: int = 10000):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_tracked_keys = max_tracked_keys
        self.attempts: dict[str, list[float]] = {}

    def _cleanup_expired(self, now: float):
        expired_keys = []
        for key, timestamps in list(self.attempts.items()):
            valid_ts = [t for t in timestamps if now - t < self.window_seconds]
            if valid_ts:
                self.attempts[key] = valid_ts
            else:
                expired_keys.append(key)
        for k in expired_keys:
            self.attempts.pop(k, None)

    def check_rate_limit(self, key: str):
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if key in self.attempts:
            # Очищаем попытки вне временного окна
            valid_attempts = [t for t in self.attempts[key] if now - t < self.window_seconds]
            if not valid_attempts:
                self.attempts.pop(key, None)
                return
            self.attempts[key] = valid_attempts

            if len(valid_attempts) >= self.max_attempts:
                oldest = min(valid_attempts)
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Слишком много неудачных попыток входа. Пожалуйста, подождите {retry_after} секунд.",
                    headers={"Retry-After": str(retry_after)}
                )

    def record_failed_attempt(self, key: str):
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if len(self.attempts) >= self.max_tracked_keys:
            self._cleanup_expired(now)
            if len(self.attempts) >= self.max_tracked_keys:
                # Если все еще переполнено, удаляем старейший ключ
                oldest_key = next(iter(self.attempts))
                self.attempts.pop(oldest_key, None)

        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(now)

    def reset(self, key: str):
        self.attempts.pop(key, None)

login_rate_limiter = LoginRateLimiter()

async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> UserSession:
    token = None
    is_cookie_auth = False
    # 1. Сначала проверяем Bearer заголовок
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    # 2. Либо Cookie сессии (удобно для браузера)
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
        is_cookie_auth = True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Защита от CSRF атак при Cookie аутентификации
    verify_csrf(request, is_cookie_auth)

    if await is_token_revoked_in_db(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен отозван при выходе из системы",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    groups = payload.get("groups", [])
    admin_groups = set(settings.acl.ui_access.admin_groups)
    is_admin = bool(set(groups) & admin_groups)

    return UserSession(
        username=payload["sub"],
        display_name=payload.get("display_name", payload["sub"]),
        email=payload.get("email"),
        groups=groups,
        is_admin=is_admin,
        auth_method=payload.get("auth_method", "unknown")
    )
