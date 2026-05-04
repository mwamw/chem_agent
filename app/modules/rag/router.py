from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db_session
from app.modules.literature.service import LiteratureService
from app.modules.rag.schemas import RAGQueryRequest
from app.modules.rag.service import RAGService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query")
async def rag_query(
    payload: RAGQueryRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    service = RAGService(LiteratureService(session))
    return await service.query(
        tenant_id=current_user.tenant_id,
        query=payload.query,
        k=payload.k or settings.rag_default_k,
        profile=payload.profile or settings.rag_profile,
    )
