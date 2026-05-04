from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.modules.activities.schemas import BioactivitySearchRequest
from app.modules.activities.service import BioactivityService

router = APIRouter(prefix="/bioactivities", tags=["bioactivities"])


@router.post("/search")
async def search_bioactivities(
    payload: BioactivitySearchRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await BioactivityService(session).search(
        current_user.tenant_id,
        target_query=payload.target_query,
        compound_query=payload.compound_query,
        limit=payload.limit,
    )
