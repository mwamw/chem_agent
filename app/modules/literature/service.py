from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.easyagent.rag_factory import build_hybrid_retriever
from app.db.models import Paper, PaperChunk


class LiteratureService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.retriever = build_hybrid_retriever()

    async def search(self, tenant_id: str, query: str, k: int = 4, profile: str = "balanced") -> dict:
        result = await self.session.execute(
            select(PaperChunk, Paper)
            .join(Paper, Paper.id == PaperChunk.paper_id)
            .where(PaperChunk.tenant_id == tenant_id)
        )
        chunks = []
        for chunk, paper in result.all():
            chunks.append(
                {
                    "chunk_id": chunk.id,
                    "paper_id": paper.id,
                    "paper_title": paper.title,
                    "section_title": chunk.section_title,
                    "content": chunk.content,
                    "metadata": {
                        "doi": paper.doi,
                        "pmid": paper.pmid,
                        "pmcid": paper.pmcid,
                        "source_url": paper.source_url,
                    },
                }
            )
        retrieved = self.retriever.retrieve(query=query, chunks=chunks, k=k, profile=profile)
        citations = []
        for item in retrieved:
            citations.append(
                {
                    "paper_id": item.paper_id,
                    "paper_title": item.paper_title,
                    "section_title": item.section_title,
                    "chunk_id": item.chunk_id,
                    "snippet": item.content[:280],
                    "metadata": item.metadata,
                    "score": round(item.score, 4),
                }
            )
        return {"query": query, "citations": citations}
