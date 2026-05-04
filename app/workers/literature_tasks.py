from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="chemintel.literature.ingest")
def ingest_literature_task(scope: str) -> dict:
    return {"status": "queued", "scope": scope}
