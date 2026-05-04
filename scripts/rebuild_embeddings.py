from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.models import PaperChunk
from app.db.session import SessionFactory
from app.integrations.embedding_client import EmbeddingClient, to_pgvector_literal


async def rebuild(tenant_id: str | None = None) -> None:
    settings = get_settings()
    client = EmbeddingClient()
    async with SessionFactory() as session:
        query = select(PaperChunk.id, PaperChunk.content)
        if tenant_id:
            query = query.where(PaperChunk.tenant_id == tenant_id)
        result = await session.execute(query.order_by(PaperChunk.paper_id, PaperChunk.chunk_index))
        chunks = result.all()
        for chunk_id, content in chunks:
            embedding = await client.embed_text(content)
            await session.execute(
                text("""
                    UPDATE paper_chunks
                    SET embedding = CAST(:embedding AS vector),
                        embedding_model = :embedding_model,
                        updated_at = now()
                    WHERE id = :chunk_id
                    """),
                {
                    "embedding": to_pgvector_literal(embedding),
                    "embedding_model": settings.embedding_model,
                    "chunk_id": chunk_id,
                },
            )
        await session.commit()
        print(f"Rebuilt embeddings for {len(chunks)} paper chunks.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild PaperChunk embeddings for pgvector search."
    )
    parser.add_argument("--tenant-id", default=None)
    args = parser.parse_args()
    asyncio.run(rebuild(args.tenant_id))


if __name__ == "__main__":
    main()
