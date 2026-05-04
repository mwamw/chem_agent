from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schemas import LoginRequest, LoginResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    result = await AuthService(session).login(payload.username, payload.display_name)
    await session.commit()
    return LoginResponse(**result)
