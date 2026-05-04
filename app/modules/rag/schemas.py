from __future__ import annotations

from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    query: str
    k: int | None = None
    profile: str | None = None
