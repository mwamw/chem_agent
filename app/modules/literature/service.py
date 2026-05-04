from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.easyagent.rag_factory import build_hybrid_retriever
from app.adapters.easyagent.retrievers import _heuristic_boost
from app.core.config import get_settings
from app.db.models import Paper, PaperChunk
from app.integrations.embedding_client import EmbeddingClient, to_pgvector_literal


class LiteratureService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.retriever = build_hybrid_retriever()
        self.embedding_client = EmbeddingClient()

    async def search(
        self, tenant_id: str, query: str, k: int = 4, profile: str = "balanced"
    ) -> dict:
        if self.settings.vector_search_enabled and not self.settings.database_url.startswith(
            "sqlite"
        ):
            try:
                citations = await self._search_pgvector(tenant_id, query, k=k, profile=profile)
                if citations:
                    return {
                        "query": query,
                        "citations": citations,
                        "retrieval_mode": "pgvector_hybrid",
                    }
            except Exception:
                pass
        fallback = await self._search_local(tenant_id, query, k=k, profile=profile)
        fallback["retrieval_mode"] = "fallback_local"
        return fallback

    async def _search_pgvector(
        self, tenant_id: str, query: str, k: int, profile: str
    ) -> list[dict]:
        queries = [query]
        if profile == "high_recall":
            queries = self.retriever._expand_queries(query)  # noqa: SLF001
        candidates: dict[str, dict] = {}
        for subquery in queries:
            embedding = await self.embedding_client.embed_text(subquery)
            vector_literal = to_pgvector_literal(embedding)
            vector_rows = await self._vector_candidates(tenant_id, vector_literal, k=max(k * 4, 12))
            lexical_rows = []
            if profile in {"balanced", "high_recall"}:
                lexical_rows = await self._lexical_candidates(tenant_id, subquery, k=max(k * 4, 12))
            for row in vector_rows + lexical_rows:
                row["score"] = float(row["score"]) + 0.2 * _heuristic_boost(
                    query, row["paper_title"], row["content"]
                )
                current = candidates.get(row["chunk_id"])
                if current is None or row["score"] > current["score"]:
                    candidates[row["chunk_id"]] = row
        ranked = sorted(candidates.values(), key=lambda row: row["score"], reverse=True)
        return [self._citation(row) for row in ranked[:k]]

    async def _vector_candidates(self, tenant_id: str, vector_literal: str, k: int) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT
                  pc.id AS chunk_id,
                  p.id AS paper_id,
                  p.title AS paper_title,
                  pc.section_title,
                  pc.content,
                  p.doi,
                  p.pmid,
                  p.pmcid,
                  p.source_url,
                  1.0 / (1.0 + (pc.embedding <=> CAST(:embedding AS vector))) AS score
                FROM paper_chunks pc
                JOIN papers p ON p.id = pc.paper_id
                WHERE pc.tenant_id = :tenant_id AND pc.embedding IS NOT NULL
                ORDER BY pc.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """),
            {"tenant_id": tenant_id, "embedding": vector_literal, "limit": k},
        )
        return [dict(row._mapping) for row in result.all()]

    async def _lexical_candidates(self, tenant_id: str, query: str, k: int) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT
                  pc.id AS chunk_id,
                  p.id AS paper_id,
                  p.title AS paper_title,
                  pc.section_title,
                  pc.content,
                  p.doi,
                  p.pmid,
                  p.pmcid,
                  p.source_url,
                  ts_rank_cd(pc.content_tsv, plainto_tsquery('english', :query)) AS score
                FROM paper_chunks pc
                JOIN papers p ON p.id = pc.paper_id
                WHERE pc.tenant_id = :tenant_id
                  AND pc.content_tsv @@ plainto_tsquery('english', :query)
                ORDER BY score DESC
                LIMIT :limit
                """),
            {"tenant_id": tenant_id, "query": query, "limit": k},
        )
        return [dict(row._mapping) for row in result.all()]

    async def _search_local(self, tenant_id: str, query: str, k: int, profile: str) -> dict:
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
            citations.append(self._citation(item.__dict__))
        return {"query": query, "citations": citations}

    @staticmethod
    def _citation(row: dict) -> dict:
        metadata = row.get("metadata") or {
            "doi": row.get("doi"),
            "pmid": row.get("pmid"),
            "pmcid": row.get("pmcid"),
            "source_url": row.get("source_url"),
        }
        return {
            "paper_id": row["paper_id"],
            "paper_title": row["paper_title"],
            "section_title": row["section_title"],
            "chunk_id": row["chunk_id"],
            "snippet": row["content"][:280],
            "metadata": metadata,
            "score": round(float(row.get("score", 0.0)), 4),
        }
