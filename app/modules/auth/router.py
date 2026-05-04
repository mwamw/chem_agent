from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    result = await AuthService(session).login(payload.username, payload.password)
    result.pop("refresh_token_id", None)
    await session.commit()
    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    result = await AuthService(session).refresh(payload.refresh_token)
    result.pop("refresh_token_id", None)
    await session.commit()
    return TokenResponse(**result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest, session: AsyncSession = Depends(get_db_session)
) -> Response:
    await AuthService(session).logout(payload.refresh_token)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(get_current_principal)) -> MeResponse:
    return MeResponse(
        user_id=principal.user.id,
        tenant_id=principal.tenant_id,
        username=principal.user.username,
        email=principal.user.email,
        display_name=principal.user.display_name,
        roles=list(principal.roles),
        permissions=sorted(principal.permissions),
    )
