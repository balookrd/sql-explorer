import uuid
import datetime
from typing import Optional, List
from pydantic import BaseModel
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.config import settings

security_bearer = HTTPBearer(auto_error=False)

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
    except JWTError:
        return None

import hashlib
from sqlalchemy import select, delete
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.models import RevokedToken

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# L1 In-memory кэш отозванных токенов для мгновенной проверки
_revoked_tokens_cache: set[str] = set()

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
    _revoked_tokens_cache.add(h)

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
            _revoked_tokens_cache.add(h)
            return True
        return False

def revoke_token(token: str):
    """Синхронная обертка для обратной совместимости"""
    _revoked_tokens_cache.add(hash_token(token))

def is_token_revoked(token: str) -> bool:
    """Синхронная проверка по L1 кэшу"""
    return hash_token(token) in _revoked_tokens_cache

class LoginRateLimiter:
    """
    Лимитер количества попыток аутентификации для защиты от Brute-force и Password Spraying.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: dict[str, list[float]] = {}

    def check_rate_limit(self, key: str):
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if key in self.attempts:
            # Очищаем попытки вне временного окна
            self.attempts[key] = [t for t in self.attempts[key] if now - t < self.window_seconds]
            if len(self.attempts[key]) >= self.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Слишком много неудачных попыток входа. Пожалуйста, подождите {self.window_seconds} секунд."
                )

    def record_failed_attempt(self, key: str):
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
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
    # 1. Сначала проверяем Bearer заголовок
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    # 2. Либо Cookie сессии (удобно для EventSource/SSE и браузера)
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    # 3. Либо query параметр token (для обратной совместимости)
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
