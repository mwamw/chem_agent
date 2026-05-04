from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Compound, CompoundSynonym


class CompoundService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve(self, tenant_id: str, query: str) -> Compound:
        synonym_subquery = select(CompoundSynonym.compound_id).where(
            CompoundSynonym.synonym.ilike(f"%{query}%")
        )
        result = await self.session.execute(
            select(Compound)
            .where(Compound.tenant_id == tenant_id)
            .where(
                or_(Compound.primary_name.ilike(f"%{query}%"), Compound.id.in_(synonym_subquery))
            )
            .order_by(Compound.primary_name.asc())
        )
        compound = result.scalars().first()
        if compound is None:
            raise NotFoundError(f"Compound not found for query: {query}")
        return compound

    async def get(self, tenant_id: str, compound_id: str) -> Compound:
        result = await self.session.execute(
            select(Compound).where(Compound.tenant_id == tenant_id, Compound.id == compound_id)
        )
        compound = result.scalar_one_or_none()
        if compound is None:
            raise NotFoundError(f"Compound not found: {compound_id}")
        return compound

    async def get_synonyms(self, compound_id: str) -> list[str]:
        result = await self.session.execute(
            select(CompoundSynonym.synonym)
            .where(CompoundSynonym.compound_id == compound_id)
            .order_by(CompoundSynonym.synonym.asc())
        )
        return list(result.scalars().all())
