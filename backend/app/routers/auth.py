from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..auth import authenticate_admin, create_access_token, resolve_session, security_scheme
from ..schemas import AuthLoginRequest, AuthLoginResponse, AuthSessionRead, AuthUserRead


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthLoginResponse)
def post_login(payload: AuthLoginRequest):
    user = authenticate_admin(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="账号或密码错误。")

    access_token, expires_at = create_access_token(user)
    return AuthLoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=AuthUserRead(username=user.username, role=user.role),
    )


@router.get("/session", response_model=AuthSessionRead)
def get_session(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)):
    user, expires_at = resolve_session(credentials)
    if user is None:
        return AuthSessionRead(authenticated=False)

    return AuthSessionRead(
        authenticated=True,
        expires_at=expires_at,
        user=AuthUserRead(username=user.username, role=user.role),
    )
