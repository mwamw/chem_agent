from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Target


class TargetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(self, tenant_id: str, query: str) -> list[Target]:
        result = await self.session.execute(
            select(Target)
            .where(Target.tenant_id == tenant_id)
            .where(or_(Target.symbol.ilike(f"%{query}%"), Target.full_name.ilike(f"%{query}%")))
            .order_by(Target.symbol.asc())
        )
        return list(result.scalars().all())

    async def get(self, tenant_id: str, target_id: str) -> Target:
        result = await self.session.execute(
            select(Target).where(Target.tenant_id == tenant_id, Target.id == target_id)
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise NotFoundError(f"Target not found: {target_id}")
        return target
