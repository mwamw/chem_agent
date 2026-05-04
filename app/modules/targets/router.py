from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.modules.targets.schemas import TargetResponse, TargetSearchRequest
from app.modules.targets.service import TargetService

router = APIRouter(prefix="/targets", tags=["targets"])


def _serialize_target(target) -> TargetResponse:
    return TargetResponse(
        id=target.id,
        symbol=target.symbol,
        full_name=target.full_name,
        organism=target.organism,
        summary=target.summary,
    )


@router.post("/search", response_model=list[TargetResponse])
async def search_targets(
    payload: TargetSearchRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await TargetService(session).search(current_user.tenant_id, payload.query)
    return [_serialize_target(row) for row in rows]


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: str,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    target = await TargetService(session).get(current_user.tenant_id, target_id)
    return _serialize_target(target)
