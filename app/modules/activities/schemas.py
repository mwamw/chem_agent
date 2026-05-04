from __future__ import annotations

from pydantic import BaseModel


class BioactivitySearchRequest(BaseModel):
    target_query: str | None = None
    compound_query: str | None = None
    limit: int = 10
