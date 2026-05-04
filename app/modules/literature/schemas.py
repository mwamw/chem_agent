from __future__ import annotations

from pydantic import BaseModel


class LiteratureSearchRequest(BaseModel):
    query: str
    k: int | None = None
    profile: str | None = None
