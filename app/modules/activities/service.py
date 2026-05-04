from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bioactivity, Compound, Target


class BioactivityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self, tenant_id: str, target_query: str | None, compound_query: str | None, limit: int = 10
    ) -> list[dict]:
        stmt = (
            select(Bioactivity, Compound, Target)
            .join(Compound, Compound.id == Bioactivity.compound_id)
            .join(Target, Target.id == Bioactivity.target_id)
            .where(Bioactivity.tenant_id == tenant_id)
        )
        if target_query:
            stmt = stmt.where(Target.symbol.ilike(f"%{target_query}%"))
        if compound_query:
            stmt = stmt.where(Compound.primary_name.ilike(f"%{compound_query}%"))
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        rows = []
        for bio, compound, target in result.all():
            rows.append(
                {
                    "bioactivity_id": bio.id,
                    "compound_id": compound.id,
                    "compound_name": compound.primary_name,
                    "target_id": target.id,
                    "target_symbol": target.symbol,
                    "activity_type": bio.activity_type,
                    "activity_value": bio.activity_value,
                    "activity_unit": bio.activity_unit,
                    "evidence_summary": bio.evidence_summary,
                }
            )
        return rows
