from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from backend.app.config import settings
from backend.app.core.security import create_access_token, get_current_user, UserSession
from backend.app.core.acl import check_ui_access
from backend.app.core.ldap_auth import authenticate_ldap
from backend.app.core.kerberos_auth import authenticate_spnego

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, response: Response):
    user_info = None

    # 1. Проверяем mock_users если включен mock режим
    if settings.auth.mode in ("mock", "hybrid"):
        for m in settings.auth.mock_users:
            if m.username == req.username and m.password == req.password:
                user_info = {
                    "username": m.username,
                    "display_name": m.display_name,
                    "email": m.email,
                    "groups": m.groups,
                    "auth_method": "mock"
                }
                break

    # 2. Если не найден в mock и включен LDAP, проверяем через LDAPS
    if not user_info and settings.auth.ldap.enabled:
        user_info = authenticate_ldap(req.username, req.password)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )

    # Проверка ACL на доступ к Web-UI
    admin_groups = set(settings.acl.ui_access.admin_groups)
    is_admin = bool(set(user_info["groups"]) & admin_groups)

    session_user = UserSession(
        username=user_info["username"],
        display_name=user_info.get("display_name", user_info["username"]),
        email=user_info.get("email"),
        groups=user_info.get("groups", []),
        is_admin=is_admin,
        auth_method=user_info.get("auth_method", "ldap")
    )

    if not check_ui_access(session_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к Web-UI запрещен политиками безопасности (ACL). Обратитесь к администратору."
        )

    # Создаем JWT
    token_data = {
        "sub": session_user.username,
        "display_name": session_user.display_name,
        "email": session_user.email,
        "groups": session_user.groups,
        "auth_method": session_user.auth_method
    }
    access_token = create_access_token(token_data)

    # Выставляем HttpOnly Cookie для удобной работы в браузере и EventSource
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.auth.jwt.expire_minutes * 60
    )

    return AuthResponse(access_token=access_token, user=session_user)

@router.get("/negotiate")
async def kerberos_negotiate(request: Request, response: Response):
    """
    Эндпоинт для Kerberos SPNEGO SSO.
    Браузер отправляет заголовок 'Authorization: Negotiate <ticket>'.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Negotiate "):
        # Просим браузер аутентифицироваться через SPNEGO
        response.headers["WWW-Authenticate"] = "Negotiate"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация Kerberos SPNEGO"
        )

    token_b64 = auth_header[len("Negotiate "):].strip()
    user_info = authenticate_spnego(token_b64)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка валидации Kerberos билета"
        )

    admin_groups = set(settings.acl.ui_access.admin_groups)
    is_admin = bool(set(user_info["groups"]) & admin_groups)

    session_user = UserSession(
        username=user_info["username"],
        display_name=user_info.get("display_name", user_info["username"]),
        email=user_info.get("email"),
        groups=user_info.get("groups", []),
        is_admin=is_admin,
        auth_method="kerberos"
    )

    if not check_ui_access(session_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен политиками ACL"
        )

    access_token = create_access_token({
        "sub": session_user.username,
        "display_name": session_user.display_name,
        "email": session_user.email,
        "groups": session_user.groups,
        "auth_method": "kerberos"
    })

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.auth.jwt.expire_minutes * 60
    )

    if user_info.get("out_token"):
        response.headers["WWW-Authenticate"] = f"Negotiate {user_info['out_token']}"

    return {"access_token": access_token, "user": session_user}

@router.get("/me", response_model=UserSession)
async def get_me(current_user: UserSession = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "ok", "message": "Успешный выход из системы"}
