from __future__ import annotations

import asyncio

from scripts.rebuild_embeddings import rebuild

from app.workers.celery_app import celery_app


@celery_app.task(name="chemintel.embedding.rebuild")
def rebuild_embeddings_task(scope: str | None = None) -> dict:
    asyncio.run(rebuild(scope))
    return {"status": "completed", "scope": scope}
