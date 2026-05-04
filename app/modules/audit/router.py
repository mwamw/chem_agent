from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = AuditService(session)
    rows = await service.list_logs(current_user.tenant_id)
    return [
        {
            "id": row.id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "detail": row.detail_json,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
