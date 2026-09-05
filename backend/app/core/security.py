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
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.auth.jwt.expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.auth.jwt.secret_key, algorithm=settings.auth.jwt.algorithm)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.auth.jwt.secret_key, algorithms=[settings.auth.jwt.algorithm])
        return payload
    except JWTError:
        return None

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
    # 3. Либо query параметр token (для SSE запросов EventSource)
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
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
