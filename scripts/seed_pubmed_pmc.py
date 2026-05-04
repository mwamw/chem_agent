from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.models import Paper, PaperChunk
from app.db.session import SessionFactory, init_db


async def main() -> None:
    await init_db()
    settings = get_settings()
    papers = json.loads(Path("data/seeds/literature/papers.json").read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        for row in papers:
            await session.merge(
                Paper(
                    id=row["id"],
                    tenant_id=settings.default_tenant_id,
                    title=row["title"],
                    abstract=row["abstract"],
                    doi=row.get("doi"),
                    pmid=row.get("pmid"),
                    pmcid=row.get("pmcid"),
                    source_url=row.get("source_url"),
                )
            )
            for idx, chunk in enumerate(row.get("chunks", [])):
                await session.merge(
                    PaperChunk(
                        tenant_id=settings.default_tenant_id,
                        paper_id=row["id"],
                        chunk_index=idx,
                        section_title=chunk["section_title"],
                        content=chunk["content"],
                    )
                )
        await session.commit()
    print("Seeded literature.")


if __name__ == "__main__":
    asyncio.run(main())
