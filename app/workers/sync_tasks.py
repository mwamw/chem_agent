from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="chemintel.sync.source")
def sync_source_task(source_name: str, scope: str) -> dict:
    return {"status": "queued", "source_name": source_name, "scope": scope}
